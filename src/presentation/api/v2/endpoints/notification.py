import asyncio
import json

from fastapi import APIRouter, Request, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from infrastructure.database.connection import get_db
from infrastructure.notifications.sse_manager import sse_manager
from presentation.dependencies.auth_deps import get_current_active_user_from_url_token

# from presentation.dependencies.auth_deps import get_current_active_user
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_5_per_minute
)

router = APIRouter()

@router.get("/stream")
async def stream_notifications(
    request: Request,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    enforce_rate_limit(limiter_5_per_minute, request)
    user = await get_current_active_user_from_url_token(token, db)
    user_id = user.id

    queue = await sse_manager.connect(user_id)

    async def event_generator():

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {"event": "notification", "data": json.dumps(data)}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""} # keepalive
        finally:
            await sse_manager.disconnect(user_id, queue)

    return EventSourceResponse(event_generator())

# @router.delete("/{id}")
# async def delete_notification(
#     request: Request,
#     current_user: Depends(get_current_active_user),
#     id: int
# ):
#     pass