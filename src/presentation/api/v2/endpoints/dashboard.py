from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from application.dashboard.queries.get_dashboard_summary import (
    GetDashboardSummaryHandler,
    GetDashboardSummaryQuery,
)
from presentation.dependencies.service_deps import get_dashboard_summary_handler

from domain.entities.user import User
from presentation.dependencies.auth_deps import get_current_active_user


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("")
@limiter.limit("10/minute")
async def get_general_data(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    handler: GetDashboardSummaryHandler = Depends(get_dashboard_summary_handler),
):
    query = GetDashboardSummaryQuery(
        user_uuid=current_user.uuid, user_id=current_user.id
    )
    summary = await handler.handle(query)

    return summary
