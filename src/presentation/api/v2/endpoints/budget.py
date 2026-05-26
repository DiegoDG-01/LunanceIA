from fastapi import APIRouter, Depends, status, Response, Request, Query
from typing import Optional, cast

from domain.entities.user import User
from application.dto.budget_dto import CreateBudgetDTO, UpdateBudgetDTO
from application.budgets.commands.create_budget import (
    CreateBudgetCommand,
    CreateBudgetHandler,
)
from application.budgets.commands.update_budget import (
    UpdateBudgetCommand,
    UpdateBudgetHandler,
)
from application.budgets.commands.delete_budget import (
    DeleteBudgetCommand,
    DeleteBudgetHandler,
)
from application.budgets.commands.state_budget import (
    StateBudgetCommand,
    StateBudgetHandler,
)
from application.budgets.queries.get_budgets import (
    GetBudgetsQuery,
    GetBudgetsHandler,
)
from application.budgets.queries.get_budget_by_id import (
    GetBudgetByIdQuery,
    GetBudgetByIdHandler,
)
from application.budgets.queries.get_budget_progress import (
    GetBudgetProgressQuery,
    GetBudgetProgressHandler,
)
from presentation.schemas.requests.budget import CreateBudgetRequest, UpdateBudgetRequest
from presentation.schemas.responses.budget import BudgetResponse, BudgetProgressResponse
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.dependencies.budget_deps import (
    get_create_budget_handler,
    get_update_budget_handler,
    get_delete_budget_handler,
    get_state_budget_handler,
    get_budgets_handler,
    get_budget_by_id_handler,
    get_budget_progress_handler,
)
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_50_per_minute,
    limiter_20_per_minute,
    limiter_5_per_minute,
)

router = APIRouter()


@router.get("/", response_model=list[BudgetResponse])
async def get_budgets(
    request: Request,
    active_only: bool = Query(False, description="Solo presupuestos activos"),
    category_id: Optional[int] = Query(None, gt=0, description="Filtrar por categoría"),
    current_user: User = Depends(get_current_active_user),
    handler: GetBudgetsHandler = Depends(get_budgets_handler),
):
    """Obtiene todos los presupuestos del usuario autenticado."""
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetBudgetsQuery(
        user_id=cast(int, current_user.id),
        active_only=active_only,
        category_id=category_id,
    )
    budgets = await handler.handle(query)
    return [BudgetResponse(**b.__dict__) for b in budgets]


@router.get("/{budget_uuid}/", response_model=BudgetResponse)
async def get_budget(
    request: Request,
    budget_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: GetBudgetByIdHandler = Depends(get_budget_by_id_handler),
):
    """Obtiene un presupuesto específico por su UUID."""
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetBudgetByIdQuery(
        budget_uuid=budget_uuid,
        user_id=cast(int, current_user.id),
    )
    budget = await handler.handle(query)
    return BudgetResponse(**budget.__dict__)


@router.get("/{budget_uuid}/progress/", response_model=BudgetProgressResponse)
async def get_budget_progress(
    request: Request,
    budget_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: GetBudgetProgressHandler = Depends(get_budget_progress_handler),
):
    """
    Retorna el progreso del presupuesto para el periodo actual:
    cuánto se ha gastado, cuánto resta, si se disparó la alerta y si se superó el límite.
    """
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetBudgetProgressQuery(
        budget_uuid=budget_uuid,
        user_id=cast(int, current_user.id),
    )
    progress = await handler.handle(query)
    return BudgetProgressResponse(**progress.__dict__)


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    request: Request,
    budget_request: CreateBudgetRequest,
    current_user: User = Depends(get_current_active_user),
    handler: CreateBudgetHandler = Depends(get_create_budget_handler),
):
    """Crea un nuevo presupuesto."""
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = CreateBudgetDTO(
        user_id=cast(int, current_user.id),
        name=budget_request.name,
        limit_amount=budget_request.limit_amount,
        period=budget_request.period,
        start_date=budget_request.start_date,
        category_id=budget_request.category_id,
        end_date=budget_request.end_date,
        alert_percentage=budget_request.alert_percentage,
    )
    command = CreateBudgetCommand(dto=dto)
    result = await handler.handle(command)
    return BudgetResponse(**result.__dict__)


@router.put(
    "/{budget_uuid}/",
    response_model=BudgetResponse,
    status_code=status.HTTP_200_OK,
)
async def update_budget(
    request: Request,
    budget_uuid: str,
    budget_request: UpdateBudgetRequest,
    current_user: User = Depends(get_current_active_user),
    handler: UpdateBudgetHandler = Depends(get_update_budget_handler),
):
    """Actualiza un presupuesto existente."""
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = UpdateBudgetDTO(
        name=budget_request.name,
        limit_amount=budget_request.limit_amount,
        period=budget_request.period,
        start_date=budget_request.start_date,
        end_date=budget_request.end_date,
        alert_percentage=budget_request.alert_percentage,
        category_id=budget_request.category_id,
    )
    command = UpdateBudgetCommand(
        budget_uuid=budget_uuid,
        user_id=cast(int, current_user.id),
        dto=dto,
    )
    result = await handler.handle(command)
    return BudgetResponse(**result.__dict__)


@router.patch("/{budget_uuid}/activate/", response_model=BudgetResponse)
async def toggle_budget_status(
    request: Request,
    budget_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: StateBudgetHandler = Depends(get_state_budget_handler),
):
    """Activa o desactiva un presupuesto."""
    enforce_rate_limit(limiter_5_per_minute, request)
    command = StateBudgetCommand(
        budget_uuid=budget_uuid,
        user_id=cast(int, current_user.id),
    )
    result = await handler.handle(command)
    return BudgetResponse(**result.__dict__)


@router.delete("/{budget_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    request: Request,
    budget_uuid: str,
    current_user: User = Depends(get_current_active_user),
    handler: DeleteBudgetHandler = Depends(get_delete_budget_handler),
):
    """Elimina un presupuesto permanentemente."""
    enforce_rate_limit(limiter_5_per_minute, request)
    command = DeleteBudgetCommand(
        budget_uuid=budget_uuid,
        user_id=cast(int, current_user.id),
    )
    await handler.handle(command)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
