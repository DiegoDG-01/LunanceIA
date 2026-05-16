from dataclasses import dataclass
from datetime import date
from typing import cast, List
from dateutil.relativedelta import relativedelta

from domain.objects.money import Money
from domain.entities.installment_purchase import InstallmentPurchase
from domain.entities.installment_charge import InstallmentCharge
from domain.repositories.account_repository import AccountRepository
from domain.repositories.user_repository import UserRepository
from domain.repositories.installment_purchase_repository import InstallmentPurchaseRepository
from domain.repositories.installment_charge_repository import InstallmentChargeRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from application.dto.installment_dto import CreateInstallmentPurchaseDTO, InstallmentChargeResponseDTO, InstallmentPurchaseResponseDTO
from shared.exceptions.domain import UserNotFoundError, AccountNotFoundError


@dataclass
class CreateInstallmentPurchaseCommand:
    dto: CreateInstallmentPurchaseDTO


class CreateInstallmentPurchaseHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        account_repository: AccountRepository,
        installment_purchase_repository: InstallmentPurchaseRepository,
        installment_charge_repository: InstallmentChargeRepository,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.installment_purchase_repository = installment_purchase_repository
        self.installment_charge_repository = installment_charge_repository
        self.uow = uow

    async def handle(self, command: CreateInstallmentPurchaseCommand) -> InstallmentPurchaseResponseDTO:
        dto = command.dto

        user = await self.user_repository.get_by_id(dto.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=dto.account_uuid, user_id=dto.user_id
        )
        if not account:
            raise AccountNotFoundError(account_uuid=dto.account_uuid)

        money = Money(dto.total_amount, dto.currency)

        purchase = InstallmentPurchase.create_new(
            user_id=cast(int, user.id),
            account_id=cast(int, account.id),
            category_id=dto.category_id,
            description=dto.description,
            total_amount=money,
            num_installments=dto.num_installments,
            installment_type=dto.installment_type,
            annual_interest_rate=dto.annual_interest_rate,
            purchase_date=dto.purchase_date,
            notes=dto.notes,
        )

        async with self.uow:
            purchase = await self.installment_purchase_repository.create(purchase)
            charges = self._generate_charges(purchase)
            charges = await self.installment_charge_repository.create_bulk(charges)

            await self.uow.commit()

        charges_dtos = [
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

        return InstallmentPurchaseResponseDTO.from_entity(
            purchase=purchase,
            account_uuid=dto.account_uuid,
            charges=charges_dtos
        )


    @staticmethod
    def _generate_charges(purchase: InstallmentPurchase) -> List[InstallmentCharge]:
        charges = []
        for i in range(purchase.num_installments):
            due_date = purchase.purchase_date + relativedelta(months=i + 1)
            charges.append(
                InstallmentCharge.create_new(
                    installment_purchase_id=cast(int, purchase.id),
                    installment_number=i + 1,
                    amount=purchase.monthly_payment,
                    due_date=due_date,
                )
            )
        return charges























