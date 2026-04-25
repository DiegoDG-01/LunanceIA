from abc import ABC, abstractmethod

class NotificationServiceInterface(ABC):
    @abstractmethod
    async def send_to_user(self, user_id: int, data: dict) -> None:
        pass