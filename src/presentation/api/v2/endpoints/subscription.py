from fastapi import (
    APIRouter,
    Depends,
    status,
    Response,
    Request,
    Query
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional

from domain.entities.user import User
from application.dto.subscription_dto import CreateSubscriptionDTO
from application.subscriptions.queries.get_subscriptions import GetSubscriptionsQuery, GetSubscriptionsHandler
from application.subscriptions.queries.get_subscription_charges import GetSubscriptionChargesQuery, GetSubscriptionChargesHandler
from application.subscriptions.commands.create_subscription import CreateSubscriptionCommand, CreateSubscriptionHandler
from application.subscriptions.commands.update_subscription import UpdateSubscriptionCommand, UpdateSubscriptionHandler
from application.subscriptions.commands.delete_subscription import DeleteSubscriptionCommand, DeleteSubscriptionHandler
from presentation.schemas.responses.subscription import SubscriptionResponse, SubscriptionChargeDetailResponse
from presentation.schemas.requests.subscription import CreateSubscriptionRequest, UpdateSubscriptionRequest
from presentation.dependencies.auth_deps import get_current_user
from presentation.dependencies.service_deps import (
    get_create_subscription_handler,
    get_subscriptions_handler,
    get_update_subscription_handler,
    get_delete_subscription_handler,
    get_subscription_charges_handler,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=list[SubscriptionResponse])
@limiter.limit("50/minute")
async def get_subscriptions(
        request: Request,
        account_uuid: Optional[str] = Query(None, description="UUID de la cuenta"),
        category_id: Optional[int] = Query(None, gt=0, description="ID de categoría"),
        active_only: bool = Query(False, description="Solo suscripciones activas"),
        limit: int = Query(100, ge=1, le=1000, description="Máximo de resultados"),
        offset: int = Query(0, ge=0, description="Offset para paginación"),
        current_user: User = Depends(get_current_user),
        handler: GetSubscriptionsHandler = Depends(get_subscriptions_handler)

):
    query = GetSubscriptionsQuery(
        user_id=current_user.id,
        account_uuid=account_uuid,
        category_id=category_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    subscriptions = await handler.handle(query)
    return [SubscriptionResponse(**subscription.__dict__) for subscription in subscriptions]


@router.get("/charges", response_model=list[SubscriptionChargeDetailResponse])
@limiter.limit("50/minute")
async def get_subscription_charges(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    handler: GetSubscriptionChargesHandler = Depends(get_subscription_charges_handler),
):
    """
    Obtiene todos los cargos de suscripciones del usuario con detalles de transacciones,
    categorías y cuentas.
    """
    query = GetSubscriptionChargesQuery(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    charges = handler.handle(query)
    return [SubscriptionChargeDetailResponse(**charge.__dict__) for charge in charges]


@router.get("/{subscription_uuid}", response_model=SubscriptionResponse)
async def get_subscription(
        request: Request,
        subscription_uuid: str,
        current_user: User = Depends(get_current_user),
        handler: GetSubscriptionsHandler = Depends(get_subscriptions_handler)
):
    pass


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_subscription(
        request: Request,
        subscription_request: CreateSubscriptionRequest,
        current_user: User = Depends(get_current_user),
        handler: CreateSubscriptionHandler = Depends(get_create_subscription_handler),
):
    """
    Crear una nueva suscripción.
    """
    # Convertir request → DTO
    dto = CreateSubscriptionDTO(
        user_id=current_user.id,
        account_uuid=subscription_request.account_uuid,
        category_id=subscription_request.category_id,
        name=subscription_request.name,
        amount=subscription_request.amount,
        frequency=subscription_request.frequency,
        start_date=subscription_request.start_date,
        end_date=subscription_request.end_date,
        billing_day=subscription_request.billing_day,
        description=subscription_request.description,
        service_url=subscription_request.service_url,
    )

    command = CreateSubscriptionCommand(dto=dto)
    result = await handler.handle(command)

    return SubscriptionResponse(**result.__dict__)


@router.put("/{subscription_uuid}", response_model=SubscriptionResponse, status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def update_subscription(
        request: Request,
        subscription_uuid: str,
        subscription_request: UpdateSubscriptionRequest,
        current_user: User = Depends(get_current_user),
        handler: UpdateSubscriptionHandler = Depends(get_update_subscription_handler),
):
    command = UpdateSubscriptionCommand(
        subscription_uuid=subscription_uuid,
        user_id=current_user.id,
        dto=subscription_request
    )

    update_subscription = await handler.handle(command)
    return SubscriptionResponse(**update_subscription.__dict__)


@router.delete("/{subscription_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
        subscription_uuid: str,
        current_user: User = Depends(get_current_user),
        handler: DeleteSubscriptionHandler = Depends(get_delete_subscription_handler),
):
    command = DeleteSubscriptionCommand(
        subscription_uuid=subscription_uuid,
        user_id=current_user.id
    )

    handler.handle(command)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
