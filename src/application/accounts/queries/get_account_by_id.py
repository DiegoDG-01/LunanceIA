from dataclasses import dataclass
from typing import cast

from application.dto.account_dto import (
    AccountResponseDTO,
    CreditCardSettingsDTO,
)
from domain.repositories.account_repository import AccountRepository
from shared.exceptions.domain import AccountNotFoundError


@dataclass
class GetAccountByIdQuery:
    """Query para obtener cuenta por ID."""

    account_uuid: str
    user_id: int


class GetAccountByIdHandler:
    """Handler para obtener cuenta por ID."""

    def __init__(self, account_repository: AccountRepository):
        self.account_repository = account_repository

    async def handle(self, query: GetAccountByIdQuery) -> AccountResponseDTO | None:
        """Ejecuta la query de obtener cuenta por ID."""
        account = await self.account_repository.get_by_uuid_and_user_id_with_settings(
            uuid=query.account_uuid,
            user_id=query.user_id,
        )

        if not account:
            raise AccountNotFoundError(account_uuid=query.account_uuid)

        cc_settings_dto = None

        if account.credit_card_settings:
            cc_settings_dto = CreditCardSettingsDTO(
                billing_cycle_day=account.credit_card_settings.billing_cycle_day,
                payment_due_day=account.credit_card_settings.payment_due_day,
                credit_limit=account.credit_card_settings.credit_limit,
                minimum_payment_percentage=account.credit_card_settings.minimum_payment_percentage,
            )

        return AccountResponseDTO(
            account_uuid=cast(str, account.uuid),
            name=account.name,
            account_type=account.account_type,
            bank_id=account.bank_id,
            bank_name=account.bank_name,
            bank_code=account.bank_code,
            current_balance=account.current_balance.amount,
            currency=account.current_balance.currency,
            is_active=account.is_active,
            credit_card_settings=cc_settings_dto,
        )
