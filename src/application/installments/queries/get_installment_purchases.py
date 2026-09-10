from collections import defaultdict
from dataclasses import dataclass
from typing import cast

from application.dto.installment_dto import (
    InstallmentChargeResponseDTO,
    InstallmentPurchaseResponseDTO,
)
from domain.repositories.account_repository import AccountRepository
from domain.repositories.installment_charge_repository import (
    InstallmentChargeRepository,
)
from domain.repositories.installment_purchase_repository import (
    InstallmentPurchaseRepository,
)
from domain.repositories.user_repository import UserRepository
from shared.exceptions.domain import UserNotFoundError


@dataclass
class GetInstallmentPurchasesQuery:
    user_id: int


class GetInstallmentPurchasesHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        account_repository: AccountRepository,
        installment_purchase_repository: InstallmentPurchaseRepository,
        installment_charge_repository: InstallmentChargeRepository,
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.installment_purchase_repository = installment_purchase_repository
        self.installment_charge_repository = installment_charge_repository

    async def handle(
        self, query: GetInstallmentPurchasesQuery
    ) -> list[InstallmentPurchaseResponseDTO]:
        user = await self.user_repository.get_by_id(query.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        purchases = await self.installment_purchase_repository.get_all_by_user_id(
            query.user_id
        )
        if not purchases:
            return []

        account_ids = {cast(int, p.account_id) for p in purchases}
        accounts = await self.account_repository.get_bulk_by_ids(
            account_ids=list(account_ids)
        )
        accounts_by_id = {acc.id: acc for acc in accounts}

        purchase_ids = [cast(int, p.id) for p in purchases]
        all_charges = await self.installment_charge_repository.get_bulk_by_purchase_ids(
            purchase_ids=purchase_ids
        )
        charges_by_purchase_id: dict[int, list] = defaultdict(list)
        for c in all_charges:
            charges_by_purchase_id[c.installment_purchase_id].append(c)

        result = []
        for purchase in purchases:
            account = accounts_by_id[cast(int, purchase.account_id)]
            charges = charges_by_purchase_id[cast(int, purchase.id)]

            charge_dtos = [
                InstallmentChargeResponseDTO(
                    uuid=c.uuid,
                    installment_number=c.installment_number,
                    amount=c.amount,
                    due_date=c.due_date,
                    paid=c.paid,
                    paid_at=c.paid_at,
                )
                for c in charges
            ]

            result.append(
                InstallmentPurchaseResponseDTO.from_entity(
                    purchase=purchase,
                    account_uuid=cast(str, account.uuid),
                    charges=charge_dtos,
                )
            )
        return result
