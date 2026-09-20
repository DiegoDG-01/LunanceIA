from typing import cast

from fastapi import APIRouter, Depends, Request

from application.dashboard.queries.get_dashboard_summary import (
    GetDashboardSummaryHandler,
    GetDashboardSummaryQuery,
)
from application.dashboard.queries.get_mobile_dashboard_summary import (
    GetMobileDashboardSummaryHandler,
    GetMobileDashboardSummaryQuery,
)
from domain.entities.users.user import User
from domain.objects.enums import APIKeyScope
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_10_per_minute,
)
from presentation.dependencies import (
    get_current_active_user,
    get_dashboard_summary_handler,
    get_mobile_dashboard_summary_handler,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.schemas.responses.dashboard import (
    DashboardSummaryResponse,
    MobileDashboardSummaryResponse,
)

router = APIRouter()


@router.get("/", response_model=DashboardSummaryResponse)
async def get_general_data(
    request: Request,
    current_user: User = Depends(require_scope(APIKeyScope.DASHBOARD_READ.value)),
    handler: GetDashboardSummaryHandler = Depends(get_dashboard_summary_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    query = GetDashboardSummaryQuery(user_id=cast(int, current_user.id))
    summary = await handler.handle(query)

    return summary


@router.get("/mobile/", response_model=MobileDashboardSummaryResponse)
async def get_genera_data_mobile(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    handler: GetMobileDashboardSummaryHandler = Depends(
        get_mobile_dashboard_summary_handler
    ),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    query = GetMobileDashboardSummaryQuery(user_id=cast(int, current_user.id))
    summary = await handler.handle(query)

    return summary
