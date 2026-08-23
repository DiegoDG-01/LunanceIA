import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import cast

from domain.entities.transaction import Transaction
from domain.objects.enums import InterestType, PositionStatus, TransactionType
from domain.objects.money import Money
from domain.entities.investment_yield import InvestmentYield
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from domain.repositories.investment_yield_repository import InvestmentYieldRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from application.investments.services.position_overflow import PositionOverflowService
from shared.utils.date import get_year_day_basis


logger = logging.getLogger(__name__)


@dataclass
class GenerateDailyYieldCommand:
    target_date: date


class GenerateDailyYieldHandler:
    """Genera el rendimiento diario de cada apartado de inversión activo.

    El rendimiento se queda dentro del apartado: a la vista capitaliza en su
    balance y a plazo fijo se acumula hasta el vencimiento.

    La excepción es el tope. Un apartado a la vista que ya llegó a su tope
    sigue rindiendo, pero ese rendimiento ya no cabe: se va por su cadena de
    destinos y lo que ningún apartado absorbe cae al saldo disponible. Por eso
    este job sí crea transacciones — una por apartado y por día mientras el
    excedente termine en el disponible — y lockea cuenta → apartado como el
    resto de los flujos.
    """

    def __init__(
        self,
        position_repository: InvestmentPositionRepository,
        investment_yield_repository: InvestmentYieldRepository,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        overflow_service: PositionOverflowService,
        uow: AbstractUnitOfWork,
    ):
        self.position_repository = position_repository
        self.investment_yield_repository = investment_yield_repository
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.overflow_service = overflow_service
        self.uow = uow

    async def handle(self, command: GenerateDailyYieldCommand) -> dict:
        today = command.target_date
        processed = 0
        skipped = 0
        overflowed = 0
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

                    # Orden de bloqueo consistente en todos los flujos:
                    # cuenta -> apartado. Se lockea siempre, aunque el apartado
                    # no tenga tope, para que el orden sea uno solo y nunca
                    # dependa de datos leídos sin lock.
                    account = await self.account_repository.get_by_id(
                        account_id=preview.account_id, for_update=True
                    )
                    if not account:
                        errors += 1
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

                    # El rendimiento se registra completo aunque no quepa: el
                    # histórico cuenta lo que el apartado ganó, y el
                    # desbordamiento es un movimiento aparte.
                    overflow = position.accrue_yield(
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

                    if overflow.amount > 0:
                        overflowed += 1
                        to_available = await self.overflow_service.spill(
                            position, overflow
                        )
                        if to_available.amount > 0:
                            account.update_balance(
                                account.current_balance.add(to_available)
                            )
                            await self.account_repository.update(account)

                            movement = Transaction.create_new(
                                user_id=account.user_id,
                                account_id=cast(int, account.id),
                                category_id=None,
                                transaction_type=TransactionType.TRANSFER,
                                amount=to_available,
                                transaction_date=today,
                                description=f"Excedente del apartado {position.name}",
                            )
                            movement.position_id = position.id
                            await self.transaction_repository.create(movement)

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
            "overflowed": overflowed,
            "errors": errors,
        }
