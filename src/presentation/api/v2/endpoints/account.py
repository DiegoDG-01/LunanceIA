from fastapi import APIRouter, Depends, HTTPException, status, Request, Query

from domain.entities.user import User
from presentation.schemas.requests.account import (
    CreateAccountRequest,
    UpdateAccountRequest,
)
from presentation.schemas.responses.account import (
    AccountResponse,
    AccountListResponse,
    AccountRecentActivityResponse,
)
from domain.objects.enums import APIKeyScope
from presentation.dependencies.auth_deps import require_scope
from presentation.dependencies import (
    get_create_account_handler,
    get_update_account_handler,
    get_delete_account_handler,
    get_user_accounts_handler,
    get_account_by_id_handler,
    get_state_account_handler,
    get_activity_account_handler,
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
from application.accounts.queries.get_account_activity import (
    GetAccountActivityQuery,
    GetAccountActivitiesHandler,
)
from application.dto.account_dto import (
    CreateAccountDTO,
    UpdateAccountDTO,
    CreditCardSettingsDTO,
    InvestmentCardSettingsDTO,
)
from typing import List, cast

from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_50_per_minute,
)

router = APIRouter()


@router.get("/", response_model=AccountListResponse)
async def get_user_accounts(
    request: Request,
    only_active: bool = False,
    limit: int = Query(50, ge=1, le=150),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_scope(APIKeyScope.ACCOUNTS_READ.value)),
    handler: GetUserAccountsHandler = Depends(get_user_accounts_handler),
):
    """Obtiene todas las cuentas del usuario."""
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetUserAccountsQuery(
        user_id=cast(int, current_user.id),
        only_active=only_active,
        limit=limit,
        offset=offset,
    )

    accounts = await handler.handle(query)

    return AccountListResponse(
        accounts=[AccountResponse(**account.__dict__) for account in accounts],
        total=len(accounts),
    )


@router.get("/{account_uuid}", response_model=AccountResponse)
async def get_account(
    request: Request,
    account_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.ACCOUNTS_READ.value)),
    handler: GetAccountByIdHandler = Depends(get_account_by_id_handler),
):
    """Obtiene una cuenta específica."""
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetAccountByIdQuery(
        account_uuid=account_uuid, user_id=cast(int, current_user.id)
    )

    account = await handler.handle(query)

    return AccountResponse(**account.__dict__)


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    request: Request,
    account_request: CreateAccountRequest,
    current_user: User = Depends(require_scope(APIKeyScope.ACCOUNTS_WRITE.value)),
    handler: CreateAccountHandler = Depends(get_create_account_handler),
):
    """Crea una nueva cuenta."""
    enforce_rate_limit(limiter_50_per_minute, request)
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
            investment_rate=account_request.investment_settings.investment_rate,
            lock_period_end_date=account_request.investment_settings.lock_period_end_date,
            maturity_date=account_request.investment_settings.maturity_date,
            early_withdrawal_penalty=account_request.investment_settings.early_withdrawal_penalty,
        )

    dto = CreateAccountDTO(
        bank_id=account_request.bank_id,
        user_id=cast(int, current_user.id),
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


@router.patch("/{account_uuid}/", response_model=AccountResponse)
async def update_account(
    request: Request,
    account_uuid: str,
    update_request: UpdateAccountRequest,
    current_user: User = Depends(require_scope(APIKeyScope.ACCOUNTS_WRITE.value)),
    handler: UpdateAccountHandler = Depends(get_update_account_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    cc_settings_dto = None
    if update_request.credit_card_settings:
        cc_settings_dto = CreditCardSettingsDTO(
            billing_cycle_day=update_request.credit_card_settings.billing_cycle_day,
            payment_due_day=update_request.credit_card_settings.payment_due_day,
            credit_limit=update_request.credit_card_settings.credit_limit,
            minimum_payment_percentage=update_request.credit_card_settings.minimum_payment_percentage,
        )

    inv_settings_dto = None
    if update_request.investment_settings:
        inv_settings_dto = InvestmentCardSettingsDTO(
            investment_type=update_request.investment_settings.investment_type,
            investment_rate=update_request.investment_settings.investment_rate,
            lock_period_end_date=update_request.investment_settings.lock_period_end_date,
            maturity_date=update_request.investment_settings.maturity_date,
            early_withdrawal_penalty=update_request.investment_settings.early_withdrawal_penalty,
        )
    """Actualiza una cuenta."""
    dto = UpdateAccountDTO(
        account_uuid=account_uuid,
        user_id=cast(int, current_user.id),
        name=update_request.name,
        bank_id=update_request.bank_id,
        current_balance=update_request.current_balance,
        credit_card_settings=cc_settings_dto,
        investment_settings=inv_settings_dto,
    )

    command = UpdateAccountCommand(dto=dto)

    account = await handler.handle(command)
    return AccountResponse(**account.__dict__)


@router.delete("/{account_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    request: Request,
    account_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.ACCOUNTS_WRITE.value)),
    handler: DeleteAccountHandler = Depends(get_delete_account_handler),
):
    """Elimina una cuenta."""
    enforce_rate_limit(limiter_50_per_minute, request)
    command = DeleteAccountCommand(
        account_uuid=account_uuid, user_id=cast(int, current_user.id)
    )

    success = await handler.handle(command)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada"
        )


@router.patch("/{account_uuid}/status/", response_model=AccountResponse)
async def activate_account(
    request: Request,
    account_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.ACCOUNTS_WRITE.value)),
    handler: StateAccountHandler = Depends(get_state_account_handler),
):
    """Activa/desactiva una cuenta."""
    enforce_rate_limit(limiter_50_per_minute, request)
    command = StateAccountCommand(
        account_uuid=account_uuid,
        user_id=cast(int, current_user.id),
    )

    account = await handler.handle(command)
    return AccountResponse(
        bank_id=account.bank_id,
        bank_name=account.bank_name,
        bank_code=account.bank_code,
        account_uuid=cast(str, account.uuid),
        name=account.name,
        account_type=account.account_type,
        current_balance=account.current_balance.amount,
        currency=account.current_balance.currency,
        is_active=account.is_active,
    )


@router.get(
    "/{account_uuid}/activity", response_model=List[AccountRecentActivityResponse]
)
async def get_account_activity(
    request: Request,
    account_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.ACCOUNTS_READ.value)),
    handler: GetAccountActivitiesHandler = Depends(get_activity_account_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetAccountActivityQuery(
        user_id=cast(int, current_user.id), account_uuid=account_uuid
    )
    activity = await handler.handle(query)

    return [AccountRecentActivityResponse(**item.__dict__) for item in activity]
