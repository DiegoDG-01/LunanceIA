from fastapi import APIRouter, Depends, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import List, Optional

from domain.entities.user import User
from application.investments.queries.get_investment_yields import (
    GetInvestmentYieldsQuery, GetInvestmentYieldsHandler
)
from application.investments.queries.get_investment_projections import (
    GetInvestmentProjectionsQuery, GetInvestmentProjectionsHandler
)
from presentation.schemas.responses.investment_yield import (
    InvestmentYieldResponse, InvestmentProjectionResponse
)
from presentation.dependencies.auth_deps import get_current_user
from presentation.dependencies.investment_yield_deps import (
    get_investment_yields_handler, get_investment_projections_handler
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/{account_id}/yields/", response_model=List[InvestmentYieldResponse])
@limiter.limit("50/minute")
async def get_investment_yields(
    request: Request,
    account_id: str,
    limit: int = Query(365, ge=1, le=1825, description="Máximo de registros (default 1 año)"),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    handler: GetInvestmentYieldsHandler = Depends(get_investment_yields_handler),
):
    query = GetInvestmentYieldsQuery(
        account_uuid=account_id,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    yields = await handler.handle(query)
    return [InvestmentYieldResponse(**y.__dict__) for y in yields]


@router.get("/{account_id}/projections/", response_model=InvestmentProjectionResponse)
@limiter.limit("30/minute")
async def get_investment_projections(
    request: Request,
    account_id: str,
    days: Optional[int] = Query(None, ge=1, le=3650, description="Días a proyectar. Si no se especifica, proyecta hasta maturity_date (o 365 días)."),
    current_user: User = Depends(get_current_user),
    handler: GetInvestmentProjectionsHandler = Depends(get_investment_projections_handler),
):
    query = GetInvestmentProjectionsQuery(
        account_uuid=account_id,
        user_id=current_user.id,
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