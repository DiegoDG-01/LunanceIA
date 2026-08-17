from typing import List, Optional, cast

from fastapi import APIRouter, Depends, Query, Request

from domain.entities.user import User
from domain.objects.enums import APIKeyScope
from application.dto.investment_position_dto import (
    CreatePositionDTO,
    LiquidatePositionDTO,
    PositionMovementDTO,
    UpdatePositionDTO,
)
from application.investments.commands.create_position import (
    CreatePositionCommand,
    CreatePositionHandler,
)
from application.investments.commands.deposit_to_position import (
    DepositToPositionCommand,
    DepositToPositionHandler,
)
from application.investments.commands.withdraw_from_position import (
    WithdrawFromPositionCommand,
    WithdrawFromPositionHandler,
)
from application.investments.commands.liquidate_position import (
    LiquidatePositionCommand,
    LiquidatePositionHandler,
)
from application.investments.commands.update_position import (
    UpdatePositionCommand,
    UpdatePositionHandler,
)
from application.investments.queries.list_positions import (
    ListPositionsQuery,
    ListPositionsHandler,
)
from application.investments.queries.get_position import (
    GetPositionQuery,
    GetPositionHandler,
)
from application.investments.queries.get_position_yields import (
    GetPositionYieldsQuery,
    GetPositionYieldsHandler,
)
from application.investments.queries.get_position_projections import (
    GetPositionProjectionsQuery,
    GetPositionProjectionsHandler,
)
from presentation.schemas.requests.investment_position import (
    CreatePositionRequest,
    PositionMovementRequest,
    UpdatePositionRequest,
)
from presentation.schemas.responses.investment_position import (
    AccountPositionsResponse,
    LiquidatePositionResponse,
    PositionProjectionResponse,
    PositionResponse,
)
from presentation.schemas.responses.investment_yield import InvestmentYieldResponse
from presentation.dependencies.auth_deps import require_scope
from presentation.dependencies.investment_position_deps import (
    get_create_position_handler,
    get_deposit_to_position_handler,
    get_withdraw_from_position_handler,
    get_liquidate_position_handler,
    get_list_positions_handler,
    get_position_handler,
    get_position_yields_handler,
    get_position_projections_handler,
    get_update_position_handler,
)

from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_10_per_minute,
    limiter_20_per_minute,
    limiter_30_per_minute,
    limiter_50_per_minute,
)

router = APIRouter()


@router.post("/", response_model=PositionResponse, status_code=201)
async def create_position(
    request: Request,
    position_request: CreatePositionRequest,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_WRITE.value)),
    handler: CreatePositionHandler = Depends(get_create_position_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    cap = position_request.cap
    dto = CreatePositionDTO(
        user_id=cast(int, current_user.id),
        account_uuid=position_request.account_uuid,
        name=position_request.name,
        position_type=position_request.position_type,
        amount=position_request.amount,
        annual_rate=position_request.annual_rate,
        interest_type=position_request.interest_type,
        term_days=position_request.term_days,
        maturity_date=position_request.maturity_date,
        lock_period_end_date=position_request.lock_period_end_date,
        early_withdrawal_penalty=position_request.early_withdrawal_penalty,
        on_maturity=position_request.on_maturity,
        currency=position_request.currency,
        max_balance=cap.max_balance if cap else None,
        overflow_action=cap.overflow_action if cap else None,
        overflow_position_uuid=cap.overflow_position_uuid if cap else None,
    )
    result = await handler.handle(CreatePositionCommand(dto=dto))
    return PositionResponse(**result.__dict__)


@router.get("/account/{account_uuid}/", response_model=AccountPositionsResponse)
async def list_positions(
    request: Request,
    account_uuid: str,
    include_liquidated: bool = Query(False),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    handler: ListPositionsHandler = Depends(get_list_positions_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    result = await handler.handle(
        ListPositionsQuery(
            account_uuid=account_uuid,
            user_id=cast(int, current_user.id),
            include_liquidated=include_liquidated,
        )
    )
    return AccountPositionsResponse(
        account_uuid=result.account_uuid,
        account_name=result.account_name,
        available_balance=result.available_balance,
        invested_balance=result.invested_balance,
        total_balance=result.total_balance,
        currency=result.currency,
        positions=[PositionResponse(**p.__dict__) for p in result.positions],
    )


@router.get("/{position_uuid}/", response_model=PositionResponse)
async def get_position(
    request: Request,
    position_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    handler: GetPositionHandler = Depends(get_position_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    result = await handler.handle(
        GetPositionQuery(
            position_uuid=position_uuid, user_id=cast(int, current_user.id)
        )
    )
    return PositionResponse(**result.__dict__)


@router.patch("/{position_uuid}/", response_model=PositionResponse)
async def update_position(
    request: Request,
    position_uuid: str,
    position_request: UpdatePositionRequest,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_WRITE.value)),
    handler: UpdatePositionHandler = Depends(get_update_position_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    cap = position_request.cap
    dto = UpdatePositionDTO(
        user_id=cast(int, current_user.id),
        position_uuid=position_uuid,
        name=position_request.name,
        # Sin "cap" en el body la configuración de tope no se toca; con
        # "cap": null se quita. Sin esta distinción, renombrar un apartado
        # borraría su tope sin querer.
        cap_provided="cap" in position_request.model_fields_set,
        max_balance=cap.max_balance if cap else None,
        overflow_action=cap.overflow_action if cap else None,
        overflow_position_uuid=cap.overflow_position_uuid if cap else None,
    )
    result = await handler.handle(UpdatePositionCommand(dto=dto))
    return PositionResponse(**result.__dict__)


@router.post("/{position_uuid}/deposit/", response_model=PositionResponse)
async def deposit_to_position(
    request: Request,
    position_uuid: str,
    movement_request: PositionMovementRequest,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_WRITE.value)),
    handler: DepositToPositionHandler = Depends(get_deposit_to_position_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = PositionMovementDTO(
        user_id=cast(int, current_user.id),
        position_uuid=position_uuid,
        amount=movement_request.amount,
        currency=movement_request.currency,
    )
    result = await handler.handle(DepositToPositionCommand(dto=dto))
    return PositionResponse(**result.__dict__)


@router.post("/{position_uuid}/withdraw/", response_model=PositionResponse)
async def withdraw_from_position(
    request: Request,
    position_uuid: str,
    movement_request: PositionMovementRequest,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_WRITE.value)),
    handler: WithdrawFromPositionHandler = Depends(get_withdraw_from_position_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = PositionMovementDTO(
        user_id=cast(int, current_user.id),
        position_uuid=position_uuid,
        amount=movement_request.amount,
        currency=movement_request.currency,
    )
    result = await handler.handle(WithdrawFromPositionCommand(dto=dto))
    return PositionResponse(**result.__dict__)


@router.post("/{position_uuid}/liquidate/", response_model=LiquidatePositionResponse)
async def liquidate_position(
    request: Request,
    position_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_WRITE.value)),
    handler: LiquidatePositionHandler = Depends(get_liquidate_position_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    dto = LiquidatePositionDTO(
        user_id=cast(int, current_user.id), position_uuid=position_uuid
    )
    result = await handler.handle(LiquidatePositionCommand(dto=dto))
    return LiquidatePositionResponse(**result.__dict__)


@router.get("/{position_uuid}/yields/", response_model=List[InvestmentYieldResponse])
async def get_position_yields(
    request: Request,
    position_uuid: str,
    limit: int = Query(
        365, ge=1, le=1825, description="Máximo de registros (default 1 año)"
    ),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    handler: GetPositionYieldsHandler = Depends(get_position_yields_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    yields = await handler.handle(
        GetPositionYieldsQuery(
            position_uuid=position_uuid,
            user_id=cast(int, current_user.id),
            limit=limit,
            offset=offset,
        )
    )
    return [InvestmentYieldResponse(**y.__dict__) for y in yields]


@router.get("/{position_uuid}/projections/", response_model=PositionProjectionResponse)
async def get_position_projections(
    request: Request,
    position_uuid: str,
    days: Optional[int] = Query(
        None,
        ge=1,
        le=3650,
        description="Días a proyectar. Si no se especifica, proyecta hasta el vencimiento (o 365 días).",
    ),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    handler: GetPositionProjectionsHandler = Depends(get_position_projections_handler),
):
    enforce_rate_limit(limiter_30_per_minute, request)
    result = await handler.handle(
        GetPositionProjectionsQuery(
            position_uuid=position_uuid,
            user_id=cast(int, current_user.id),
            project_days=days,
        )
    )
    return PositionProjectionResponse(
        position_uuid=result.position_uuid,
        name=result.name,
        current_value=result.current_value,
        annual_rate=result.annual_rate,
        interest_type=result.interest_type,
        maturity_date=result.maturity_date,
        projected_final_balance=result.projected_final_balance,
        daily_projections=[p.__dict__ for p in result.daily_projections],
        projected_overflow=result.projected_overflow,
        max_balance=result.max_balance,
    )
