from typing import cast

from fastapi import APIRouter, Depends, Query, Request, Response, status

from application.dto.saving_goal_dto import CreateSavingGoalDTO, UpdateSavingGoalDTO
from application.goals.commands.create_saving_goal import (
    CreateSavingGoalCommand,
    CreateSavingGoalHandler,
)
from application.goals.commands.delete_saving_goal import (
    DeleteSavingGoalCommand,
    DeleteSavingGoalHandler,
)
from application.goals.commands.state_saving_goal import (
    StateSavingGoalCommand,
    StateSavingGoalHandler,
)
from application.goals.commands.update_saving_goal import (
    UpdateSavingGoalCommand,
    UpdateSavingGoalHandler,
)
from application.goals.queries.get_saving_goal_by_id import (
    GetSavingGoalByIdHandler,
    GetSavingGoalQuery,
)
from application.goals.queries.get_saving_goals import (
    GetSavingGoalsHandler,
    GetSavingGoalsQuery,
)
from domain.entities.user import User
from domain.objects.enums import APIKeyScope
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_5_per_minute,
    limiter_20_per_minute,
    limiter_50_per_minute,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.dependencies.saving_goal_deps import (
    get_create_saving_goal_handler,
    get_delete_saving_goal_handler,
    get_saving_goals_by_id_handler,
    get_saving_goals_handler,
    get_state_saving_goal_handler,
    get_update_saving_goal_handler,
)
from presentation.schemas.requests.saving_goal import (
    SavingGoalRequest,
    UpdateSavingGoalRequest,
)
from presentation.schemas.responses.saving_goal import SavingGoalResponse

router = APIRouter()


@router.get("/", response_model=list[SavingGoalResponse])
async def get_saving_goals(
    request: Request,
    active_only: bool = Query(False, description="Solo metas activas"),
    current_user: User = Depends(require_scope(APIKeyScope.GOALS_READ.value)),
    handler: GetSavingGoalsHandler = Depends(get_saving_goals_handler),
):
    """Obtiene todas las metas de ahorro del usuario autenticado."""
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetSavingGoalsQuery(
        user_id=cast(int, current_user.id),
        active_only=active_only,
    )
    goals = await handler.handle(query)
    return [SavingGoalResponse(**g.__dict__) for g in goals]


@router.get("/{goal_uuid}/", response_model=SavingGoalResponse)
async def get_saving_goal(
    request: Request,
    goal_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.GOALS_READ.value)),
    handler: GetSavingGoalByIdHandler = Depends(get_saving_goals_by_id_handler),
):
    """Obtiene una meta de ahorro específica por su UUID."""
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetSavingGoalQuery(
        user_id=cast(int, current_user.id),
        goal_uuid=goal_uuid,
    )
    goal = await handler.handle(query)
    return SavingGoalResponse(**goal.__dict__)


@router.post(
    "/", response_model=SavingGoalResponse, status_code=status.HTTP_201_CREATED
)
async def create_saving_goal(
    request: Request,
    goal_request: SavingGoalRequest,
    current_user: User = Depends(require_scope(APIKeyScope.GOALS_WRITE.value)),
    handler: CreateSavingGoalHandler = Depends(get_create_saving_goal_handler),
):
    """Crea una nueva meta de ahorro."""
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = CreateSavingGoalDTO(
        user_id=cast(int, current_user.id),
        account_uuid=goal_request.account_uuid,
        name=goal_request.name,
        target_amount=goal_request.target_amount,
        target_date=goal_request.target_date,
        description=goal_request.description,
    )
    command = CreateSavingGoalCommand(dto=dto)
    result = await handler.handle(command)
    return SavingGoalResponse(**result.__dict__)


@router.put("/{goal_uuid}/", response_model=SavingGoalResponse)
async def update_saving_goal(
    request: Request,
    goal_uuid: str,
    goal_request: UpdateSavingGoalRequest,
    current_user: User = Depends(require_scope(APIKeyScope.GOALS_WRITE.value)),
    handler: UpdateSavingGoalHandler = Depends(get_update_saving_goal_handler),
):
    """Actualiza una meta de ahorro existente."""
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = UpdateSavingGoalDTO(
        name=goal_request.name,
        target_amount=goal_request.target_amount,
        target_date=goal_request.target_date,
        description=goal_request.description,
    )
    command = UpdateSavingGoalCommand(
        goal_uuid=goal_uuid,
        user_id=cast(int, current_user.id),
        dto=dto,
    )
    result = await handler.handle(command)
    return SavingGoalResponse(**result.__dict__)


@router.patch("/{goal_uuid}/activate/", response_model=SavingGoalResponse)
async def toggle_saving_goal_status(
    request: Request,
    goal_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.GOALS_WRITE.value)),
    handler: StateSavingGoalHandler = Depends(get_state_saving_goal_handler),
):
    """Activa o desactiva una meta de ahorro."""
    enforce_rate_limit(limiter_5_per_minute, request)
    command = StateSavingGoalCommand(
        goal_uuid=goal_uuid,
        user_id=cast(int, current_user.id),
    )
    result = await handler.handle(command)
    return SavingGoalResponse(**result.__dict__)


@router.delete("/{goal_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saving_goal(
    request: Request,
    goal_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.GOALS_WRITE.value)),
    handler: DeleteSavingGoalHandler = Depends(get_delete_saving_goal_handler),
):
    """Elimina una meta de ahorro permanentemente."""
    enforce_rate_limit(limiter_5_per_minute, request)
    command = DeleteSavingGoalCommand(
        saving_goal_uuid=goal_uuid,
        user_id=cast(int, current_user.id),
    )
    await handler.handle(command)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
