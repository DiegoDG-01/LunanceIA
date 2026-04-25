from application.interfaces.notification_service import NotificationServiceInterface
from infrastructure.notifications.sse_manager import sse_manager


class SSENotificationService(NotificationServiceInterface):
    async def send_to_user(self, user_id: int, data: dict) -> None:
        await sse_manager.send_to_user(user_id, data)