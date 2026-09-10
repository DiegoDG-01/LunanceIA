from typing import cast

from fastapi import APIRouter, Depends, Query, Request, Response, status

from application.dto.recurring_income_dto import (
    CreateRecurringIncomeDTO,
    UpdateRecurringIncomeDTO,
)
from application.incomes.commands.create_recurring_income import (
    CreateRecurringIncomeCommand,
    CreateRecurringIncomeHandler,
)
from application.incomes.commands.delete_recurring_income import (
    DeleteRecurringIncomeCommand,
    DeleteRecurringIncomeHandler,
)
from application.incomes.commands.state_recurring_income import (
    StateRecurringIncomeCommand,
    StateRecurringIncomeHandler,
)
from application.incomes.commands.update_recurring_income import (
    UpdateRecurringIncomeCommand,
    UpdateRecurringIncomeHandler,
)
from application.incomes.queries.get_income_deposits import (
    GetIncomeDepositsHandler,
    GetIncomeDepositsQuery,
)
from application.incomes.queries.get_recurring_income_by_id import (
    GetRecurringIncomeByIdHandler,
    GetRecurringIncomeByIdQuery,
)
from application.incomes.queries.get_recurring_incomes import (
    GetRecurringIncomesHandler,
    GetRecurringIncomesQuery,
)
from domain.entities.user import User
from domain.objects.enums import APIKeyScope
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_5_per_minute,
    limiter_20_per_minute,
    limiter_50_per_minute,
)
from presentation.dependencies import (
    get_create_recurring_income_handler,
    get_delete_recurring_income_handler,
    get_income_deposits_handler,
    get_recurring_income_by_id_handler,
    get_recurring_incomes_handler,
    get_state_recurring_income_handler,
    get_update_recurring_income_handler,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.schemas.requests.recurring_income import (
    CreateRecurringIncomeRequest,
    UpdateRecurringIncomeRequest,
)
from presentation.schemas.responses.recurring_income import (
    IncomeDepositResponse,
    RecurringIncomeResponse,
)

router = APIRouter()


@router.get("/", response_model=list[RecurringIncomeResponse])
async def get_recurring_incomes(
    request: Request,
    account_uuid: str | None = Query(None, description="UUID de la cuenta"),
    category_id: int | None = Query(None, gt=0, description="ID de categoría"),
    active_only: bool = Query(False, description="Solo ingresos activos"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    current_user: User = Depends(require_scope(APIKeyScope.INCOMES_READ.value)),
    handler: GetRecurringIncomesHandler = Depends(get_recurring_incomes_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetRecurringIncomesQuery(
        user_id=cast(int, current_user.id),
        account_uuid=account_uuid,
        category_id=category_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    incomes = await handler.handle(query)
    return [RecurringIncomeResponse(**income.__dict__) for income in incomes]


@router.get("/{income_uuid}/", response_model=RecurringIncomeResponse)
async def get_recurring_income(
    request: Request,
    income_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.INCOMES_READ.value)),
    handler: GetRecurringIncomeByIdHandler = Depends(
        get_recurring_income_by_id_handler
    ),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetRecurringIncomeByIdQuery(
        user_id=cast(int, current_user.id), income_uuid=income_uuid
    )

    income = await handler.handle(query)
    return RecurringIncomeResponse(**income.__dict__)


@router.get(
    "/{income_uuid}/deposits/",
    response_model=list[IncomeDepositResponse],
)
async def get_income_deposits(
    request: Request,
    income_uuid: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_scope(APIKeyScope.INCOMES_READ.value)),
    handler: GetIncomeDepositsHandler = Depends(get_income_deposits_handler),
):
    """Historial de depósitos generados por un ingreso recurrente."""
    enforce_rate_limit(limiter_20_per_minute, request)
    query = GetIncomeDepositsQuery(
        income_uuid=income_uuid,
        user_id=cast(int, current_user.id),
        limit=limit,
        offset=offset,
    )
    deposits = await handler.handle(query)
    return [IncomeDepositResponse(**deposit.__dict__) for deposit in deposits]


@router.post(
    "/", response_model=RecurringIncomeResponse, status_code=status.HTTP_201_CREATED
)
async def create_recurring_income(
    request: Request,
    income_request: CreateRecurringIncomeRequest,
    current_user: User = Depends(require_scope(APIKeyScope.INCOMES_WRITE.value)),
    handler: CreateRecurringIncomeHandler = Depends(
        get_create_recurring_income_handler
    ),
):
    """Crear un nuevo ingreso recurrente (nómina, renta, etc.)."""
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = CreateRecurringIncomeDTO(
        user_id=cast(int, current_user.id),
        account_uuid=income_request.account_uuid,
        category_id=income_request.category_id,
        name=income_request.name,
        amount=income_request.amount,
        frequency=income_request.frequency,
        start_date=income_request.start_date,
        end_date=income_request.end_date,
        next_payment_date=income_request.next_payment_date,
        description=income_request.description,
    )

    command = CreateRecurringIncomeCommand(dto=dto)
    result = await handler.handle(command)

    return RecurringIncomeResponse(**result.__dict__)


@router.patch(
    "/{income_uuid}/",
    response_model=RecurringIncomeResponse,
    status_code=status.HTTP_200_OK,
)
async def update_recurring_income(
    request: Request,
    income_uuid: str,
    income_request: UpdateRecurringIncomeRequest,
    current_user: User = Depends(require_scope(APIKeyScope.INCOMES_WRITE.value)),
    handler: UpdateRecurringIncomeHandler = Depends(
        get_update_recurring_income_handler
    ),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = UpdateRecurringIncomeDTO(
        account_uuid=income_request.account_uuid,
        name=income_request.name,
        amount=income_request.amount,
        frequency=income_request.frequency,
        start_date=income_request.start_date,
        end_date=income_request.end_date,
        next_payment_date=income_request.next_payment_date,
        is_active=income_request.is_active,
        description=income_request.description,
        category_id=income_request.category_id,
    )
    command = UpdateRecurringIncomeCommand(
        income_uuid=income_uuid,
        user_id=cast(int, current_user.id),
        dto=dto,
    )

    updated_income = await handler.handle(command)
    return RecurringIncomeResponse(**updated_income.__dict__)


@router.patch("/{income_uuid}/activate/", response_model=RecurringIncomeResponse)
async def activate_recurring_income(
    request: Request,
    income_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.INCOMES_WRITE.value)),
    handler: StateRecurringIncomeHandler = Depends(get_state_recurring_income_handler),
):
    enforce_rate_limit(limiter_5_per_minute, request)
    command = StateRecurringIncomeCommand(
        income_uuid=income_uuid, user_id=cast(int, current_user.id)
    )

    income = await handler.handle(command)
    return RecurringIncomeResponse(**income.__dict__)


@router.delete("/{income_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_income(
    request: Request,
    income_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.INCOMES_WRITE.value)),
    handler: DeleteRecurringIncomeHandler = Depends(
        get_delete_recurring_income_handler
    ),
):
    enforce_rate_limit(limiter_5_per_minute, request)
    command = DeleteRecurringIncomeCommand(
        income_uuid=income_uuid, user_id=cast(int, current_user.id)
    )

    await handler.handle(command)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
