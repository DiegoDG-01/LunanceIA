from fastapi import APIRouter, Depends, Query, Request
from typing import List, Optional, cast

from domain.entities.user import User
from domain.objects.enums import APIKeyScope
from application.investments.queries.get_investment_yields import (
    GetInvestmentYieldsQuery,
    GetInvestmentYieldsHandler,
)
from application.investments.queries.get_investment_projections import (
    GetInvestmentProjectionsQuery,
    GetInvestmentProjectionsHandler,
)
from presentation.schemas.responses.investment_yield import (
    InvestmentYieldResponse,
    InvestmentProjectionResponse,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.dependencies.investment_yield_deps import (
    get_investment_yields_handler,
    get_investment_projections_handler,
)

from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_50_per_minute,
    limiter_30_per_minute,
)

router = APIRouter()


@router.get("/{account_id}/yields/", response_model=List[InvestmentYieldResponse])
async def get_investment_yields(
    request: Request,
    account_id: str,
    limit: int = Query(
        365, ge=1, le=1825, description="Máximo de registros (default 1 año)"
    ),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    handler: GetInvestmentYieldsHandler = Depends(get_investment_yields_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetInvestmentYieldsQuery(
        account_uuid=account_id,
        user_id=cast(int, current_user.id),
        limit=limit,
        offset=offset,
    )
    yields = await handler.handle(query)
    return [InvestmentYieldResponse(**y.__dict__) for y in yields]


@router.get("/{account_id}/projections/", response_model=InvestmentProjectionResponse)
async def get_investment_projections(
    request: Request,
    account_id: str,
    days: Optional[int] = Query(
        None,
        ge=1,
        le=3650,
        description="Días a proyectar. Si no se especifica, proyecta hasta maturity_date (o 365 días).",
    ),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    handler: GetInvestmentProjectionsHandler = Depends(
        get_investment_projections_handler
    ),
):
    enforce_rate_limit(limiter_30_per_minute, request)
    query = GetInvestmentProjectionsQuery(
        account_uuid=account_id,
        user_id=cast(int, current_user.id),
        project_days=days,
    )

    result = await handler.handle(query)
    return InvestmentProjectionResponse(
        account_uuid=result.account_uuid,
        current_balance=result.current_balance,
        annual_rate=result.annual_rate,
        interest_type=result.interest_type,
        maturity_date=result.maturity_date,
        projected_final_balance=result.projected_final_balance,
        daily_projections=[p.__dict__ for p in result.daily_projections],
    )
