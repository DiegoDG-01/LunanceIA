import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

from application.notifications.queries.get_and_clear_notifications import (
    GetAndClearNotificationsQuery,
    GetAndClearNotificationsHandler,
)
from domain.entities.notification import Notification
from domain.objects.enums import NotificationType


@pytest.mark.unit
class TestGetAndClearNotificationsHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "notification_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return GetAndClearNotificationsHandler(
            notification_repository=mocks["notification_repo"],
            uow=mocks["uow"],
        )

    def _make_notification(self, notif_id: int = 1) -> Notification:
        return Notification(
            id=notif_id,
            user_id=1,
            title=f"Notification {notif_id}",
            message="Your subscription was charged",
            type=NotificationType.PUSH,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_returns_and_clears_notifications(self, handler, mocks):
        notifications = [self._make_notification(1), self._make_notification(2)]
        mocks["notification_repo"].get_by_user_id = AsyncMock(return_value=notifications)
        mocks["notification_repo"].delete_by_user_id = AsyncMock()

        query = GetAndClearNotificationsQuery(user_id=1)
        result = await handler.handle(query)

        assert len(result) == 2
        assert result[0].title == "Notification 1"
        mocks["notification_repo"].delete_by_user_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_notifications(self, handler, mocks):
        mocks["notification_repo"].get_by_user_id = AsyncMock(return_value=[])

        query = GetAndClearNotificationsQuery(user_id=1)
        result = await handler.handle(query)

        assert result == []
        mocks["notification_repo"].delete_by_user_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_not_called_when_empty(self, handler, mocks):
        mocks["notification_repo"].get_by_user_id = AsyncMock(return_value=[])
        mocks["notification_repo"].delete_by_user_id = AsyncMock()

        query = GetAndClearNotificationsQuery(user_id=1)
        await handler.handle(query)

        mocks["notification_repo"].delete_by_user_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_queries_correct_user_id(self, handler, mocks):
        mocks["notification_repo"].get_by_user_id = AsyncMock(return_value=[])

        query = GetAndClearNotificationsQuery(user_id=42)
        await handler.handle(query)

        mocks["notification_repo"].get_by_user_id.assert_called_once_with(42)
