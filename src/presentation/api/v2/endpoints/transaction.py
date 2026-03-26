from fastapi import (
    APIRouter,
    Depends,
    status,
    Response,
    Request,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

from application.transactions.queries.get_transactions import GetTransactionsQuery
from application.transactions.queries.get_transactions import GetTransactionsHandler
from domain.entities.user import User
from application.dto.transaction_dto import CreateTransactionDTO
from presentation.schemas.responses.transaction import TransactionResponse
from presentation.schemas.requests.transaction import CreateTransactionRequest
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.dependencies import (
    get_create_transaction_handler,
    get_transactions_handler,
    get_delete_transaction_handler,
    get_transaction_by_uuid_handler,
)
from application.transactions.commands.delete_transaction import (
    DeleteTransactionCommand,
    DeleteTransactionHandler,
)
from application.transactions.commands.create_transaction import (
    CreateTransactionCommand,
    CreateTransactionHandler,
)
from application.transactions.queries.get_transaction_by_uuid import (
    GetTransactionByUuidQuery,
    GetTransactionByUuidHandler,
)
from typing import Optional
from datetime import date
from fastapi import Query
from domain.objects.enums import TransactionType

from presentation.schemas.requests.transaction import UpdateTransactionRequest
from application.transactions.commands.update_transaction import (
    UpdateTransactionCommand,
    UpdateTransactionCommandHandler,
)
from presentation.dependencies import get_update_transaction_handler
from shared.exceptions.domain import TransactionNotFoundError

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=list[TransactionResponse])
@limiter.limit("50/minute")
async def get_transactions(
    request: Request,
    # 📥 QUERY PARAMETERS: Recibe filtros del HTTP request
    skip: int = Query(0, ge=0, description="Saltar N transacciones"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo de resultados"),
    start_date: Optional[date] = Query(None, description="Filtrar desde esta fecha"),
    end_date: Optional[date] = Query(None, description="Filtrar hasta esta fecha"),
    transaction_type: Optional[TransactionType] = Query(
        None, description="Tipo de transacción"
    ),
    category_id: Optional[int] = Query(None, gt=0, description="ID de categoría"),
    account_uuid: Optional[str] = Query(None, description="UUID de la cuenta"),
    # 🔐 DEPENDENCIAS: Inyección automática de FastAPI
    current_user: User = Depends(get_current_active_user),
    handler: GetTransactionsHandler = Depends(get_transactions_handler),
):
    """
    🌐 ENDPOINT HTTP: Punto de entrada para obtener transacciones
    ✨ Función: Valida input → crea query → ejecuta caso de uso → formatea response
    """

    # 📦 Crear el query object con todos los filtros
    query = GetTransactionsQuery(
        user_id=current_user.id,  # 🔒 Del token JWT
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
        category_id=category_id,
        account_uuid=account_uuid,
    )

    # ⚙️ Ejecutar el caso de uso
    transactions = await handler.handle(query)

    # 📤 Convertir DTOs → Response schema para HTTP
    return [TransactionResponse(**transaction.__dict__) for transaction in transactions]


@router.get("/{transaction_uuid}/", response_model=TransactionResponse)
@limiter.limit("50/minute")
async def get_transaction_by_uuid(
    request: Request,
    transaction_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: GetTransactionByUuidHandler = Depends(get_transaction_by_uuid_handler),
):
    query = GetTransactionByUuidQuery(uuid=transaction_uuid, user_id=current_user.id)

    transaction = await handler.handle(query)
    return TransactionResponse(**transaction.__dict__)


@router.post("/", response_model=TransactionResponse)
@limiter.limit("20/minute")
async def create_transaction(
    request: Request,
    transaction_request: CreateTransactionRequest,
    current_user: User = Depends(get_current_active_user),
    handler: CreateTransactionHandler = Depends(get_create_transaction_handler),
):
    # Convertir request → DTO
    dto = CreateTransactionDTO(
        account_uuid=transaction_request.account_uuid,
        user_id=current_user.id,
        category_id=transaction_request.category_id,
        transaction_type=transaction_request.transaction_type,
        amount=transaction_request.amount,
        description=transaction_request.description,
        notes=transaction_request.notes,
        transaction_date=transaction_request.transaction_date,
    )

    command = CreateTransactionCommand(dto=dto)
    result = await handler.handle(command)

    return TransactionResponse(**result.__dict__)


@router.put("/{transaction_uuid}/", response_model=TransactionResponse)
@limiter.limit("15/minute")
async def update_transaction(
    request: Request,
    transaction_uuid: str,
    update_request: UpdateTransactionRequest,
    current_user: User = Depends(get_current_active_user),
    handler: UpdateTransactionCommandHandler = Depends(get_update_transaction_handler),
):
    command = UpdateTransactionCommand(
        transaction_uuid=transaction_uuid,
        user_id=current_user.id,
        description=update_request.description,
        notes=update_request.notes,
        category_id=update_request.category_id,
        transaction_type=update_request.transaction_type,
        amount=update_request.amount,
        transaction_date=update_request.transaction_date,
    )

    updated_transaction = await handler.handle(command)
    return TransactionResponse(**updated_transaction.__dict__)


@router.delete("/{transaction_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_transaction(
    request: Request,
    transaction_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: DeleteTransactionHandler = Depends(get_delete_transaction_handler),
):
    """
    Elimina una transacción específica.

    - **transaction_uuid**: UUID de la transacción a eliminar
    - Requiere ownership: solo el dueño puede eliminar
    - Retorna 204 si exitoso, 404 si no encontrado
    """
    command = DeleteTransactionCommand(uuid=transaction_uuid, user_id=current_user.id)

    deleted = await handler.handle(command)

    if not deleted:
        raise TransactionNotFoundError(command.uuid)

    # 204 No Content - successful deletion
    return Response(status_code=status.HTTP_204_NO_CONTENT)
