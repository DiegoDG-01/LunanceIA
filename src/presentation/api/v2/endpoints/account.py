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
from presentation.dependencies.service_deps import (
    get_create_account_handler,
    get_update_account_handler,
    get_delete_account_handler,
    get_user_accounts_handler,
    get_account_by_id_handler,
    get_state_account_handler,
)
from application.commands.create_account_command import (
    CreateAccountCommand,
    CreateAccountHandler,
)
from application.commands.state_account_command import (
    StateAccountCommand,
    StateAccountHandler,
)
from application.commands.update_account_command import (
    UpdateAccountCommand,
    UpdateAccountHandler,
)
from application.commands.delete_account_command import (
    DeleteAccountCommand,
    DeleteAccountHandler,
)
from application.queries.get_user_accounts_query import (
    GetUserAccountsQuery,
    GetUserAccountsHandler,
)
from application.queries.get_account_by_id_query import (
    GetAccountByIdQuery,
    GetAccountByIdHandler,
)
from application.dto.account_dto import CreateAccountDTO, UpdateAccountDTO

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=AccountListResponse)
@limiter.limit("1000/minute")
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
@limiter.limit("1000/minute")
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
@limiter.limit("1000/minute")
async def create_account(
    request: Request,
    account_request: CreateAccountRequest,
    current_user: User = Depends(get_current_active_user),
    handler: CreateAccountHandler = Depends(get_create_account_handler),
):
    """Crea una nueva cuenta."""
    dto = CreateAccountDTO(
        user_id=current_user.id,
        name=account_request.name,
        account_type=account_request.account_type,
        bank=account_request.bank,
        initial_balance=account_request.initial_balance,
        currency=account_request.currency,
    )

    command = CreateAccountCommand(dto=dto)

    account = await handler.handle(command)
    return AccountResponse(**account.__dict__)


@router.patch("/{account_uuid}", response_model=AccountResponse)
@limiter.limit("1000/minute")
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
        bank=update_request.bank,
        current_balance=update_request.current_balance,
    )

    command = UpdateAccountCommand(dto=dto)

    account = await handler.handle(command)
    return AccountResponse(**account.__dict__)


@router.delete("/{account_uuid}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("1000/minute")
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


@router.patch("/{account_uuid}/status", response_model=AccountResponse)
@limiter.limit("1000/minute")
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
        account_uuid=account.uuid,
        name=account.name,
        account_type=account.account_type,
        bank=account.bank,
        current_balance=account.current_balance.amount,
        currency=account.current_balance.currency,
        is_active=account.is_active,
    )
