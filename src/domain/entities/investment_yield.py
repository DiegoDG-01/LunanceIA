from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from domain.objects.enums import InterestType


@dataclass
class InvestmentYield:
    id: int | None
    uuid: str | None
    account_id: int
    yield_date: date
    principal_amount: Decimal  # Balance utilizado como base de calculo
    yield_amount: Decimal  # Rendimiento generado en el dia
    cumulative_balance: Decimal  # principal_amount + yield_amount
    annual_rate: Decimal  # Taza anual usada (snapshot del dia)
    interest_type: InterestType
    created_at: datetime | None = None
    position_id: int | None = None  # Apartado que generó el rendimiento

    @classmethod
    def create_new(
        cls,
        account_id: int,
        yield_date: date,
        principal_amount: Decimal,
        yield_amount: Decimal,
        cumulative_balance: Decimal,
        annual_rate: Decimal,
        interest_type: InterestType,
        position_id: int | None = None,
    ) -> "InvestmentYield":
        return cls(
            id=None,
            uuid=None,
            account_id=account_id,
            yield_date=yield_date,
            principal_amount=principal_amount,
            yield_amount=yield_amount,
            cumulative_balance=cumulative_balance,
            annual_rate=annual_rate,
            interest_type=interest_type,
            created_at=None,
            position_id=position_id,
        )
