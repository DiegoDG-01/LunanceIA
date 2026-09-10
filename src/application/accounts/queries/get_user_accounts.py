from dataclasses import dataclass
from typing import cast

from application.dto.account_dto import (
    AccountResponseDTO,
    CreditCardSettingsDTO,
)
from domain.repositories.account_repository import AccountRepository


@dataclass
class GetUserAccountsQuery:
    """Query para obtener cuentas de usuario."""

    user_id: int
    only_active: bool = False
    limit: int = 50
    offset: int = 0


class GetUserAccountsHandler:
    """Handler para obtener cuentas de usuario."""

    def __init__(
        self,
        account_repository: AccountRepository,
    ):
        self.account_repository = account_repository

    async def handle(self, query: GetUserAccountsQuery) -> list[AccountResponseDTO]:
        """Ejecuta la query de obtener cuentas."""
        if query.only_active:
            accounts = await self.account_repository.get_active_by_user(
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset,
            )
        else:
            accounts = await self.account_repository.get_by_user_id(
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset,
            )

        result = []
        for account in accounts:
            cc_settings_dto = None

            if account.credit_card_settings:
                cc_settings_dto = CreditCardSettingsDTO(
                    billing_cycle_day=account.credit_card_settings.billing_cycle_day,
                    payment_due_day=account.credit_card_settings.payment_due_day,
                    credit_limit=account.credit_card_settings.credit_limit,
                    minimum_payment_percentage=account.credit_card_settings.minimum_payment_percentage,
                )

            result.append(
                AccountResponseDTO(
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
            )
        return result
