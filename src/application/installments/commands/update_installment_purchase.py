from dataclasses import dataclass
from typing import Optional, cast

from application.dto.installment_dto import (
    InstallmentPurchaseResponseDTO,
    InstallmentChargeResponseDTO,
)
from domain.repositories.account_repository import AccountRepository
from domain.repositories.installment_charge_repository import (
    InstallmentChargeRepository,
)
from domain.repositories.installment_purchase_repository import (
    InstallmentPurchaseRepository,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import AccountNotFoundError


@dataclass
class UpdateInstallmentPurchaseCommand:
    user_id: int
    purchase_uuid: str
    category_id: Optional[int] = None
    description: Optional[str] = None
    notes: Optional[str] = None


class UpdateInstallmentPurchaseHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        installment_purchase_repository: InstallmentPurchaseRepository,
        installment_charge_repository: InstallmentChargeRepository,
        uow: AbstractUnitOfWork,
    ):
        self.account_repository = account_repository
        self.installment_purchase_repository = installment_purchase_repository
        self.installment_charge_repository = installment_charge_repository
        self.uow = uow

    async def handle(
        self, command: UpdateInstallmentPurchaseCommand
    ) -> InstallmentPurchaseResponseDTO:
        purchase = await self.installment_purchase_repository.get_by_uuid(
            uuid=command.purchase_uuid, user_id=command.user_id
        )
        if not purchase:
            raise ValueError("Purchase not found")

        account = await self.account_repository.get_by_id(purchase.account_id)
        if not account:
            raise AccountNotFoundError(account_uuid=str(purchase.account_id))

        if command.description is not None:
            purchase.description = command.description
        if command.notes is not None:
            purchase.notes = command.notes
        if command.category_id is not None:
            purchase.category_id = command.category_id

        async with self.uow:
            purchase = await self.installment_purchase_repository.update(purchase)
            await self.uow.commit()

        charges = await self.installment_charge_repository.get_by_purchase_id(
            purchase_id=cast(int, purchase.id)
        )
        charges_dtos = [
            InstallmentChargeResponseDTO(
                uuid=cast(str, c.uuid),
                installment_number=c.installment_number,
                amount=c.amount,
                due_date=c.due_date,
                paid=c.paid,
                paid_at=c.paid_at,
            )
            for c in charges
        ]

        return InstallmentPurchaseResponseDTO.from_entity(
            purchase=purchase,
            account_uuid=cast(str, account.uuid),
            charges=charges_dtos,
        )
