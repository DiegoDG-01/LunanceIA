from pydantic import BaseModel
from datetime import datetime
from domain.objects.enums import NotificationType


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: NotificationType
    created_at: datetime

    model_config = {"from_attributes": True}