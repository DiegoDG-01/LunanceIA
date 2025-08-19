from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    HTTPException,
    status,
    Response,
    Request,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

from infrastructure.external_services.gemini import GeminiService

from application.queries.get_transactions_query import GetTransactionsQuery
from application.queries.get_transactions_query import GetTransactionsHandler
from domain.entities.user import User
from application.dto.transaction_dto import CreateTransactionDTO
from presentation.schemas.responses.transaction import TransactionResponse
from presentation.schemas.requests.transaction import CreateTransactionRequest
from presentation.dependencies.auth_deps import get_current_user
from presentation.dependencies.service_deps import (
    get_create_transaction_handler,
    get_gemini_service,
    get_transactions_handler,
    get_delete_transaction_handler,
    get_transaction_by_uuid_handler,
)
from application.commands.delete_transaction_command import (
    DeleteTransactionCommand,
    DeleteTransactionHandler,
)
from application.commands.create_transaction_command import (
    CreateTransactionCommand,
    CreateTransactionHandler,
)
from application.queries.get_transaction_by_uuid_query import (
    GetTransactionByUuidQuery,
    GetTransactionByUuidHandler,
)
from typing import Optional
from datetime import date
from fastapi import Query
from domain.objects.enums import TransactionType


from presentation.schemas.requests.transaction import UpdateTransactionRequest
from application.commands.update_transaction_command import (
    UpdateTransactionCommand,
    UpdateTransactionCommandHandler,
)
from presentation.dependencies.service_deps import get_update_transaction_handler
from shared.exceptions.domain import (
    GeminiInvalidResponseError,
    GeminiProcessingError,
    GeminiAPIError,
    InvalidImageError,
    AccountNotFoundError,
    UserNotFoundError,
    TransactionNotFoundError,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=list[TransactionResponse])
@limiter.limit("100/minute")
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
    current_user: User = Depends(get_current_user),
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
    transactions = handler.handle(query)

    # 📤 Convertir DTOs → Response schema para HTTP
    return [TransactionResponse(**transaction.__dict__) for transaction in transactions]


@router.get("/{transaction_uuid}", response_model=TransactionResponse)
@limiter.limit("100/minute")
async def get_transaction_by_uuid(
    request: Request,
    transaction_uuid: str,
    current_user: User = Depends(get_current_user),
    handler: GetTransactionByUuidHandler = Depends(get_transaction_by_uuid_handler),
):
    query = GetTransactionByUuidQuery(uuid=transaction_uuid, user_id=current_user.id)

    transaction = await handler.handle(query)
    return TransactionResponse(**transaction.__dict__)


@router.post("/", response_model=TransactionResponse)
@limiter.limit("50/minute")
async def create_transaction(
    request: Request,
    transaction_request: CreateTransactionRequest,
    current_user: User = Depends(get_current_user),
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


@router.post("/image", response_model=TransactionResponse)
@limiter.limit("10/minute")  # Más restrictivo por ser procesamiento de imagen
async def create_transaction_from_image(
    request: Request,
    file: UploadFile = File(...),
    account_uuid: str = Form(...),
    current_user: User = Depends(get_current_user),
    gemini_service: GeminiService = Depends(get_gemini_service),
    handler: CreateTransactionHandler = Depends(get_create_transaction_handler),
):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # 1. Leer imagen
    image_data = await file.read()

    # 2. Procesar con Gemini
    try:
        gemini_result = await gemini_service.extract_transaction_data(image_data)
    except InvalidImageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GeminiAPIError:
        raise HTTPException(
            status_code=502, detail="External service temporarily unavailable"
        )
    except GeminiInvalidResponseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except GeminiProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 3. Create DTO combining Gemini + request
    dto = CreateTransactionDTO(
        user_id=current_user.id,
        account_uuid=account_uuid,
        category_id=gemini_result.category_id,
        transaction_type=gemini_result.transaction_type,
        amount=gemini_result.amount,
        description=gemini_result.description,
        notes=gemini_result.notes,
        transaction_date=gemini_result.transaction_date,
    )

    try:
        # 4. Ejecutar mismo comando
        command = CreateTransactionCommand(dto=dto)
        result = await handler.handle(command)
    except (ValueError, AccountNotFoundError, UserNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TransactionResponse(**result.__dict__)


@router.put("/{transaction_uuid}", response_model=TransactionResponse)
@limiter.limit("30/minute")
async def update_transaction(
    request: Request,
    transaction_uuid: str,
    update_request: UpdateTransactionRequest,
    current_user: User = Depends(get_current_user),
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

    try:
        updated_transaction = handler.handle(command)
        return TransactionResponse(**updated_transaction.__dict__)
    except TransactionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction not found or access denied",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating transaction",
        )


@router.delete("/{transaction_uuid}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_transaction(
    request: Request,
    transaction_uuid: str,
    current_user: User = Depends(get_current_user),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    # 204 No Content - successful deletion
    return Response(status_code=status.HTTP_204_NO_CONTENT)
