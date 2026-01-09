from fastapi import (
    APIRouter,
    Depends,
    status,
    Request,
    Query
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional

from domain.entities.user import User
from application.dto.subscription_dto import CreateSubscriptionDTO
from application.queries.get_subscriptions_query import GetSubscriptionsQuery, GetSubscriptionsHandler
from application.commands.create_subscription_command import CreateSubscriptionCommand, CreateSubscriptionHandler
from presentation.schemas.responses.subscription import SubscriptionResponse
from presentation.schemas.requests.subscription import CreateSubscriptionRequest
from presentation.dependencies.auth_deps import get_current_user
from presentation.dependencies.service_deps import get_create_subscription_handler, get_subscriptions_handler

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
