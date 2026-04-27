from typing import List, cast

from fastapi import APIRouter, Depends, Request

from application.notifications.queries.get_and_clear_notifications import (
    GetAndClearNotificationsHandler,
    GetAndClearNotificationsQuery,
)
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.dependencies.notification_deps import get_notifications_handler
from presentation.schemas.responses.notification import NotificationResponse
from domain.entities.user import User
from infrastructure.rate_limiting.limiters import enforce_rate_limit, limiter_5_per_minute

router = APIRouter()


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    handler: GetAndClearNotificationsHandler = Depends(get_notifications_handler),
):
    enforce_rate_limit(limiter_5_per_minute, request)
    return await handler.handle(
        GetAndClearNotificationsQuery(user_id=cast(int, current_user.id))
    )