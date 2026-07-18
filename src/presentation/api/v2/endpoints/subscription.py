from fastapi import APIRouter, Depends, status, Response, Request, Query
from typing import Optional, List, cast

from domain.entities.user import User
from domain.objects.enums import APIKeyScope
from application.dto.subscription_dto import (
    CreateSubscriptionDTO,
    UpdateSubscriptionDTO,
)
from application.subscriptions.queries.get_subscriptions_by_id import (
    GetSubscriptionsByIdQuery,
    GetSubscriptionsByIdHandler,
)
from application.subscriptions.queries.get_subscriptions import (
    GetSubscriptionsQuery,
    GetSubscriptionsHandler,
)
from application.subscriptions.queries.get_subscription_charges import (
    GetSubscriptionChargesQuery,
    GetSubscriptionChargesHandler,
)
from application.subscriptions.commands.create_subscription import (
    CreateSubscriptionCommand,
    CreateSubscriptionHandler,
)
from application.subscriptions.commands.update_subscription import (
    UpdateSubscriptionCommand,
    UpdateSubscriptionHandler,
)
from application.subscriptions.commands.delete_subscription import (
    DeleteSubscriptionCommand,
    DeleteSubscriptionHandler,
)
from application.subscriptions.commands.state_subscription import (
    StateSubscriptionCommand,
    StateSubscriptionHandler,
)
from application.subscriptions.queries.get_last_transactions import (
    GetLastTransactionsQuery,
    GetLastTransactionsHandler,
)
from presentation.schemas.responses.subscription import (
    SubscriptionResponse,
    SubscriptionChargeDetailResponse,
)
from presentation.schemas.requests.subscription import (
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.dependencies import (
    get_create_subscription_handler,
    get_subscriptions_handler,
    get_update_subscription_handler,
    get_delete_subscription_handler,
    get_subscription_charges_handler,
    get_subscription_by_id_handler,
    get_state_subscription_handler,
    get_last_transactions_handler,
)
from presentation.schemas.responses.subscription import SubscriptionLastChargeResponse

from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_50_per_minute,
    limiter_20_per_minute,
    limiter_5_per_minute,
)

router = APIRouter()


@router.get("/", response_model=list[SubscriptionResponse])
async def get_subscriptions(
    request: Request,
    account_uuid: Optional[str] = Query(None, description="UUID de la cuenta"),
    category_id: Optional[int] = Query(None, gt=0, description="ID de categoría"),
    active_only: bool = Query(False, description="Solo suscripciones activas"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    current_user: User = Depends(require_scope(APIKeyScope.SUBSCRIPTIONS_READ.value)),
    handler: GetSubscriptionsHandler = Depends(get_subscriptions_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetSubscriptionsQuery(
        user_id=cast(int, current_user.id),
        account_uuid=account_uuid,
        category_id=category_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    subscriptions = await handler.handle(query)
    return [
        SubscriptionResponse(**subscription.__dict__) for subscription in subscriptions
    ]


@router.get("/charges/", response_model=list[SubscriptionChargeDetailResponse])
async def get_subscription_charges(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_scope(APIKeyScope.SUBSCRIPTIONS_READ.value)),
    handler: GetSubscriptionChargesHandler = Depends(get_subscription_charges_handler),
):
    """
    Obtiene todos los cargos de suscripciones del usuario con detalles de transacciones,
    categorías y cuentas.
    """
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetSubscriptionChargesQuery(
        user_id=cast(int, current_user.id),
        limit=limit,
        offset=offset,
    )

    charges = await handler.handle(query)
    return [SubscriptionChargeDetailResponse(**charge.__dict__) for charge in charges]


@router.get("/{subscription_uuid}/", response_model=SubscriptionResponse)
async def get_subscription(
    request: Request,
    subscription_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.SUBSCRIPTIONS_READ.value)),
    handler: GetSubscriptionsByIdHandler = Depends(get_subscription_by_id_handler),
):
    query = GetSubscriptionsByIdQuery(
        user_id=cast(int, current_user.id), subscription_uuid=subscription_uuid
    )

    subscription = await handler.handle(query)
    return SubscriptionResponse(**subscription.__dict__)


@router.post(
    "/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_subscription(
    request: Request,
    subscription_request: CreateSubscriptionRequest,
    current_user: User = Depends(require_scope(APIKeyScope.SUBSCRIPTIONS_WRITE.value)),
    handler: CreateSubscriptionHandler = Depends(get_create_subscription_handler),
):
    """
    Crear una nueva suscripción.
    """
    enforce_rate_limit(limiter_20_per_minute, request)
    # Convertir request → DTO
    dto = CreateSubscriptionDTO(
        user_id=cast(int, current_user.id),
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


@router.patch(
    "/{subscription_uuid}/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def update_subscription(
    request: Request,
    subscription_uuid: str,
    subscription_request: UpdateSubscriptionRequest,
    current_user: User = Depends(require_scope(APIKeyScope.SUBSCRIPTIONS_WRITE.value)),
    handler: UpdateSubscriptionHandler = Depends(get_update_subscription_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = UpdateSubscriptionDTO(
        account_uuid=subscription_request.account_uuid,
        name=subscription_request.name,
        amount=subscription_request.amount,
        frequency=subscription_request.frequency,
        start_date=subscription_request.start_date,
        end_date=subscription_request.end_date,
        billing_day=subscription_request.billing_day,
        is_active=subscription_request.is_active,
        description=subscription_request.description,
        service_url=subscription_request.service_url,
        category_id=subscription_request.category_id,
    )
    command = UpdateSubscriptionCommand(
        subscription_uuid=subscription_uuid,
        user_id=cast(int, current_user.id),
        dto=dto,
    )

    update_subscription = await handler.handle(command)
    return SubscriptionResponse(**update_subscription.__dict__)


@router.patch("/{subscription_uuid}/activate/", response_model=SubscriptionResponse)
async def activate_subscription(
    request: Request,
    subscription_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.SUBSCRIPTIONS_WRITE.value)),
    handler: StateSubscriptionHandler = Depends(get_state_subscription_handler),
):
    enforce_rate_limit(limiter_5_per_minute, request)
    command = StateSubscriptionCommand(
        subscription_uuid=subscription_uuid, user_id=cast(int, current_user.id)
    )

    subscription = await handler.handle(command)
    return SubscriptionResponse(**subscription.__dict__)


@router.delete("/{subscription_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    request: Request,
    subscription_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.SUBSCRIPTIONS_WRITE.value)),
    handler: DeleteSubscriptionHandler = Depends(get_delete_subscription_handler),
):
    enforce_rate_limit(limiter_5_per_minute, request)
    command = DeleteSubscriptionCommand(
        subscription_uuid=subscription_uuid, user_id=cast(int, current_user.id)
    )

    await handler.handle(command)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{subscription_uuid}/transactions/",
    response_model=List[SubscriptionLastChargeResponse],
)
async def get_subscription_last_charge(
    request: Request,
    subscription_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.SUBSCRIPTIONS_READ.value)),
    handler: GetLastTransactionsHandler = Depends(get_last_transactions_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    query = GetLastTransactionsQuery(
        subscription_uuid=subscription_uuid, user_id=cast(int, current_user.id)
    )
    result = await handler.handle(query)

    return [SubscriptionLastChargeResponse(**item.__dict__) for item in result]
