from fastapi import APIRouter, Depends, HTTPException, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from domain.entities.user import User
from presentation.schemas.requests.account import (
    CreateAccountRequest,
    UpdateAccountRequest,
)
from presentation.schemas.responses.account import AccountResponse, AccountListResponse
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.dependencies import (
    get_create_account_handler,
    get_update_account_handler,
    get_delete_account_handler,
    get_user_accounts_handler,
    get_account_by_id_handler,
    get_state_account_handler,
)
from application.accounts.commands.create_account import (
    CreateAccountCommand,
    CreateAccountHandler,
)
from application.accounts.commands.state_account import (
    StateAccountCommand,
    StateAccountHandler,
)
from application.accounts.commands.update_account import (
    UpdateAccountCommand,
    UpdateAccountHandler,
)
from application.accounts.commands.delete_account import (
    DeleteAccountCommand,
    DeleteAccountHandler,
)
from application.accounts.queries.get_user_accounts import (
    GetUserAccountsQuery,
    GetUserAccountsHandler,
)
from application.accounts.queries.get_account_by_id import (
    GetAccountByIdQuery,
    GetAccountByIdHandler,
)
from application.dto.account_dto import (
    CreateAccountDTO,
    UpdateAccountDTO,
    CreditCardSettingsDTO,
    InvestmentCardSettingsDTO,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=AccountListResponse)
@limiter.limit("50/minute")
async def get_user_accounts(
    request: Request,
    only_active: bool = False,
    current_user: User = Depends(get_current_active_user),
    handler: GetUserAccountsHandler = Depends(get_user_accounts_handler),
):
    """Obtiene todas las cuentas del usuario."""
    query = GetUserAccountsQuery(user_id=current_user.id, only_active=only_active)

    accounts = await handler.handle(query)

    return AccountListResponse(
        accounts=[AccountResponse(**account.__dict__) for account in accounts],
        total=len(accounts),
    )


@router.get("/{account_uuid}", response_model=AccountResponse)
@limiter.limit("50/minute")
async def get_account(
    request: Request,
    account_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: GetAccountByIdHandler = Depends(get_account_by_id_handler),
):
    """Obtiene una cuenta específica."""
    query = GetAccountByIdQuery(account_uuid=account_uuid, user_id=current_user.id)

    account = await handler.handle(query)

    return AccountResponse(**account.__dict__)


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("50/minute")
async def create_account(
    request: Request,
    account_request: CreateAccountRequest,
    current_user: User = Depends(get_current_active_user),
    handler: CreateAccountHandler = Depends(get_create_account_handler),
):
    """Crea una nueva cuenta."""
    cc_settings_dto = None
    if account_request.credit_card_settings:
        cc_settings_dto = CreditCardSettingsDTO(
            billing_cycle_day=account_request.credit_card_settings.billing_cycle_day,
            payment_due_day=account_request.credit_card_settings.payment_due_day,
            credit_limit=account_request.credit_card_settings.credit_limit,
            minimum_payment_percentage=account_request.credit_card_settings.minimum_payment_percentage,
        )

    inv_settings_dto = None
    if account_request.investment_settings:
        inv_settings_dto = InvestmentCardSettingsDTO(
            investment_type=account_request.investment_settings.investment_type,
            interest_rate=account_request.investment_settings.interest_rate,
            lock_period_end_date=account_request.investment_settings.lock_period_end_date,
            maturity_date=account_request.investment_settings.maturity_date,
            early_withdrawal_penalty=account_request.investment_settings.early_withdrawal_penalty,
        )

    dto = CreateAccountDTO(
        bank_id=account_request.bank_id,
        user_id=current_user.id,
        name=account_request.name,
        account_type=account_request.account_type,
        initial_balance=account_request.initial_balance,
        currency=account_request.currency,
        credit_card_settings=cc_settings_dto,
        investment_settings=inv_settings_dto,
    )

    command = CreateAccountCommand(dto=dto)
    account = await handler.handle(command)

    return AccountResponse(**account.__dict__)


# @router.patch("/{account_uuid}/settings/", response_model=AccountResponse)
# async def update_account_settings(
#         account_uuid: str,
#         settings_request: UpdateAccountSettingsRequest,
#         current_user: User = Depends(get_current_active_user),
#         handler: UpdateAccountSettingsHandler = Depends(get_update_account_settings_handler),
# )


@router.patch("/{account_uuid}/", response_model=AccountResponse)
@limiter.limit("50/minute")
async def update_account(
    request: Request,
    account_uuid: str,
    update_request: UpdateAccountRequest,
    current_user: User = Depends(get_current_active_user),
    handler: UpdateAccountHandler = Depends(get_update_account_handler),
):
    """Actualiza una cuenta."""
    dto = UpdateAccountDTO(
        account_uuid=account_uuid,
        user_id=current_user.id,
        name=update_request.name,
        bank_id=update_request.bank_id,
        current_balance=update_request.current_balance,
    )

    command = UpdateAccountCommand(dto=dto)

    account = await handler.handle(command)
    return AccountResponse(**account.__dict__)


@router.delete("/{account_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("50/minute")
async def delete_account(
    request: Request,
    account_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: DeleteAccountHandler = Depends(get_delete_account_handler),
):
    """Elimina una cuenta."""
    command = DeleteAccountCommand(account_uuid=account_uuid, user_id=current_user.id)

    success = await handler.handle(command)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada"
        )


@router.patch("/{account_uuid}/status/", response_model=AccountResponse)
@limiter.limit("50/minute")
async def activate_account(
    request: Request,
    account_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: StateAccountHandler = Depends(get_state_account_handler),
):
    """Activa/desactiva una cuenta."""
    command = StateAccountCommand(
        account_uuid=account_uuid,
        user_id=current_user.id,
    )

    account = await handler.handle(command)
    return AccountResponse(
        bank_id=account.bank_id,
        bank_name=account.bank_name,
        bank_code=account.bank_code,
        account_uuid=account.uuid,
        name=account.name,
        account_type=account.account_type,
        current_balance=account.current_balance.amount,
        currency=account.current_balance.currency,
        is_active=account.is_active,
    )
