from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.objects.enums import NotificationType


@dataclass
class Notification:
    id: Optional[int]
    user_id: int
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: Optional[datetime] = None

    @classmethod
    def create_new(
        cls,
        user_id: int,
        title: str,
        message: str,
        type: NotificationType,
        is_read: bool = False,
    ):
        return cls(
            id=None,
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            is_read=is_read,
        )
