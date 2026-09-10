from typing import cast

from fastapi import APIRouter, Depends, Request

from application.dashboard.queries.get_dashboard_summary import (
    GetDashboardSummaryHandler,
    GetDashboardSummaryQuery,
)
from domain.entities.user import User
from domain.objects.enums import APIKeyScope
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_10_per_minute,
)
from presentation.dependencies import get_dashboard_summary_handler
from presentation.dependencies.auth_deps import require_scope
from presentation.schemas.responses.dashboard import DashboardSummaryResponse

router = APIRouter()


@router.get("/", response_model=DashboardSummaryResponse)
async def get_general_data(
    request: Request,
    current_user: User = Depends(require_scope(APIKeyScope.DASHBOARD_READ.value)),
    handler: GetDashboardSummaryHandler = Depends(get_dashboard_summary_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    query = GetDashboardSummaryQuery(
        user_uuid=current_user.uuid, user_id=cast(int, current_user.id)
    )
    summary = await handler.handle(query)

    return summary
