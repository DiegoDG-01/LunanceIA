import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import cast

from domain.objects.enums import InterestType, PositionStatus
from domain.objects.money import Money
from domain.entities.investment_yield import InvestmentYield
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from domain.repositories.investment_yield_repository import InvestmentYieldRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.utils.date import get_year_day_basis


logger = logging.getLogger(__name__)


@dataclass
class GenerateDailyYieldCommand:
    target_date: date


class GenerateDailyYieldHandler:
    """Genera el rendimiento diario de cada apartado de inversión activo.

    El rendimiento no toca el saldo disponible de la cuenta: a la vista
    capitaliza dentro del apartado y a plazo fijo se acumula hasta el
    vencimiento. Por eso este job ya no crea transacciones; el dinero
    aparece como transacción cuando cruza al disponible (liquidación o
    vencimiento).
    """

    def __init__(
        self,
        position_repository: InvestmentPositionRepository,
        investment_yield_repository: InvestmentYieldRepository,
        uow: AbstractUnitOfWork,
    ):
        self.position_repository = position_repository
        self.investment_yield_repository = investment_yield_repository
        self.uow = uow

    async def handle(self, command: GenerateDailyYieldCommand) -> dict:
        today = command.target_date
        processed = 0
        skipped = 0
        errors = 0

        previews = await self.position_repository.get_active_positions()

        async with self.uow:
            for preview in previews:
                try:
                    # Un plazo vencido deja de rendir; el job de vencimientos
                    # decide qué hacer con él (el día del vencimiento sí rinde).
                    if preview.maturity_date and today > preview.maturity_date:
                        skipped += 1
                        continue

                    # Idempotency: Does today's yield already exist?
                    existing = (
                        await self.investment_yield_repository.get_by_position_and_date(
                            position_id=cast(int, preview.id), yield_date=today
                        )
                    )
                    if existing:
                        skipped += 1
                        continue

                    # Re-obtener con lock para no pisar depósitos/retiros
                    # concurrentes calculando sobre un objeto obsoleto.
                    position = await self.position_repository.get_by_id(
                        position_id=cast(int, preview.id), for_update=True
                    )
                    if not position or position.status != PositionStatus.ACTIVE:
                        skipped += 1
                        continue

                    annual_rate = position.annual_rate
                    year_basis = Decimal(get_year_day_basis(today))

                    if position.interest_type == InterestType.COMPOUND:
                        principal = position.total_value.amount
                        daily_rate = (1 + annual_rate / Decimal(100)) ** (
                            Decimal(1) / year_basis
                        ) - Decimal(1)
                    else:
                        principal = position.base_principal or position.balance.amount
                        daily_rate = annual_rate / Decimal(100) / year_basis

                    yield_amount = (principal * daily_rate).quantize(Decimal("0.01"))

                    if yield_amount <= 0:
                        skipped += 1
                        continue

                    position.accrue_yield(
                        Money(yield_amount, position.balance.currency)
                    )
                    yield_record = InvestmentYield.create_new(
                        account_id=position.account_id,
                        position_id=cast(int, position.id),
                        yield_date=today,
                        principal_amount=principal,
                        yield_amount=yield_amount,
                        cumulative_balance=position.total_value.amount,
                        annual_rate=annual_rate,
                        interest_type=position.interest_type,
                    )

                    await self.position_repository.update(position)
                    await self.investment_yield_repository.create(yield_record)

                    processed += 1
                    logger.info(f"generated daily yield for position {position.id}")

                except Exception as e:
                    errors += 1
                    logger.error(
                        f"failed to generate daily yield for position {preview.id}: {e}",
                        exc_info=True,
                    )

            await self.uow.commit()

        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
        }
