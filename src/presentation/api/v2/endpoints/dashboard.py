from fastapi import APIRouter, Depends, Request
from typing import cast

from application.dashboard.queries.get_dashboard_summary import (
    GetDashboardSummaryHandler,
    GetDashboardSummaryQuery,
)
from presentation.dependencies import get_dashboard_summary_handler

from domain.entities.user import User
from presentation.dependencies.auth_deps import get_current_active_user


from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_10_per_minute,
)

router = APIRouter()


@router.get("/")
async def get_general_data(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    handler: GetDashboardSummaryHandler = Depends(get_dashboard_summary_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    query = GetDashboardSummaryQuery(
        user_uuid=cast(str, current_user.uuid), user_id=cast(int, current_user.id)
    )
    summary = await handler.handle(query)

    return summary
