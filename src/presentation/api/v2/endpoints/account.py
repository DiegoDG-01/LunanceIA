from fastapi import APIRouter, Depends, HTTPException, status

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


@router.get("/", response_model=AccountListResponse)
async def get_user_accounts(
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
async def get_account(
    account_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: GetAccountByIdHandler = Depends(get_account_by_id_handler),
):
    """Obtiene una cuenta específica."""
    query = GetAccountByIdQuery(account_uuid=account_uuid, user_id=current_user.id)

    account = await handler.handle(query)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada"
        )

    return AccountResponse(**account.__dict__)


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    request: CreateAccountRequest,
    current_user: User = Depends(get_current_active_user),
    handler: CreateAccountHandler = Depends(get_create_account_handler),
):
    """Crea una nueva cuenta."""
    dto = CreateAccountDTO(
        user_id=current_user.id,
        name=request.name,
        account_type=request.account_type,
        bank=request.bank,
        initial_balance=request.initial_balance,
        currency=request.currency,
    )

    command = CreateAccountCommand(dto=dto)

    try:
        account = await handler.handle(command)
        return AccountResponse(**account.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{account_uuid}", response_model=AccountResponse)
async def update_account(
    account_uuid: str,
    request: UpdateAccountRequest,
    current_user: User = Depends(get_current_active_user),
    handler: UpdateAccountHandler = Depends(get_update_account_handler),
):
    """Actualiza una cuenta."""
    dto = UpdateAccountDTO(
        account_uuid=account_uuid,
        user_id=current_user.id,
        name=request.name,
        bank=request.bank,
        current_balance=request.current_balance,
    )

    command = UpdateAccountCommand(dto=dto)

    try:
        account = await handler.handle(command)
        return AccountResponse(**account.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{account_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: DeleteAccountHandler = Depends(get_delete_account_handler),
):
    """Elimina una cuenta."""
    command = DeleteAccountCommand(account_uuid=account_uuid, user_id=current_user.id)

    try:
        success = await handler.handle(command)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada"
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{account_uuid}/status", response_model=AccountResponse)
async def activate_account(
    account_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: StateAccountHandler = Depends(get_state_account_handler),
):
    """Activa/desactiva una cuenta."""
    command = StateAccountCommand(
        account_uuid=account_uuid,
        user_id=current_user.id,
        status=True,
    )

    try:
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

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
