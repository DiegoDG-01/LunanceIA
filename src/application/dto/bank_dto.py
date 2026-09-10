from dataclasses import dataclass

from domain.entities.bank import Bank


@dataclass
class BankResponseDTO:
    id: int
    name: str
    code: str
    country: str
    logo_url: str | None
    color: str | None
    is_active: bool

    @classmethod
    def from_entity(cls, bank: Bank) -> "BankResponseDTO":
        return cls(
            id=bank.id,
            name=bank.name,
            code=bank.code,
            country=bank.country,
            logo_url=bank.logo_url,
            color=bank.color,
            is_active=bank.is_active,
        )
