import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime, timezone

from application.subscriptions.commands.delete_subscription import (
    DeleteSubscriptionCommand,
    DeleteSubscriptionHandler,
)
from domain.entities.subscription import Subscription
from domain.objects.enums import Frequency
from domain.objects.money import Money
from shared.exceptions.domain import SubscriptionNotFoundError


@pytest.mark.unit
class TestDeleteSubscriptionHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "subscription_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return DeleteSubscriptionHandler(
            subscription_repository=mocks["subscription_repo"],
            uow=mocks["uow"],
        )

    def _make_subscription(self) -> Subscription:
        return Subscription(
            id=1, uuid="sub-uuid-1", user_id=1, account_id=10, category_id=1,
            name="Netflix", amount=Money(Decimal("199.00")),
            frequency=Frequency.MONTHLY, start_date=date.today(),
            end_date=None, billing_day=1, is_active=True,
            description=None, service_url=None, creation_date=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_delete_success(self, handler, mocks):
        subscription = self._make_subscription()
        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=subscription
        )
        mocks["subscription_repo"].delete = AsyncMock(return_value=True)

        command = DeleteSubscriptionCommand(subscription_uuid="sub-uuid-1", user_id=1)
        result = await handler.handle(command)

        assert result is True
        mocks["subscription_repo"].delete.assert_called_once_with(
            uuid="sub-uuid-1", user_id=1
        )

    @pytest.mark.asyncio
    async def test_raises_subscription_not_found(self, handler, mocks):
        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        command = DeleteSubscriptionCommand(subscription_uuid="fake-uuid", user_id=1)

        with pytest.raises(SubscriptionNotFoundError):
            await handler.handle(command)

        mocks["subscription_repo"].delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_delete_returns_false(self, handler, mocks):
        subscription = self._make_subscription()
        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=subscription
        )
        mocks["subscription_repo"].delete = AsyncMock(return_value=False)

        command = DeleteSubscriptionCommand(subscription_uuid="sub-uuid-1", user_id=1)

        with pytest.raises(SubscriptionNotFoundError):
            await handler.handle(command)
