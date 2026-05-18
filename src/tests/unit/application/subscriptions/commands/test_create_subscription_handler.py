import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime, timezone

from application.subscriptions.commands.create_subscription import (
    CreateSubscriptionCommand,
    CreateSubscriptionHandler,
)
from application.dto.subscription_dto import CreateSubscriptionDTO
from domain.entities.account import Account
from domain.entities.category import Category
from domain.entities.subscription import Subscription
from domain.entities.user import User
from domain.objects.enums import AccountType, Frequency
from domain.objects.money import Money
from shared.exceptions.domain import UserNotFoundError, AccountNotFoundError


@pytest.mark.unit
class TestCreateSubscriptionHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "subscription_repo": MagicMock(),
            "user_repo": MagicMock(),
            "account_repo": MagicMock(),
            "category_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return CreateSubscriptionHandler(
            subscription_repository=mocks["subscription_repo"],
            user_repository=mocks["user_repo"],
            account_repository=mocks["account_repo"],
            category_repository=mocks["category_repo"],
            uow=mocks["uow"],
        )

    def _make_user(self, is_active: bool = True) -> User:
        return User(
            id=1, uuid="u-1", auth0_id="a-1", name="Test", email="t@t.com",
            is_active=is_active
        )

    def _make_account(self) -> Account:
        acc = Account(
            id=10, uuid="acc-uuid-1", user_id=1, bank_id=1,
            name="Test Account", account_type=AccountType.CHECKING,
            current_balance=Money(Decimal("5000.00")), is_active=True,
            creation_date=datetime.now(timezone.utc),
        )
        acc.uuid = "acc-uuid-1"
        return acc

    def _make_subscription(self) -> Subscription:
        return Subscription(
            id=1, uuid="sub-uuid-1", user_id=1, account_id=10, category_id=1,
            name="Netflix", amount=Money(Decimal("199.00")),
            frequency=Frequency.MONTHLY, start_date=date.today(),
            end_date=None, billing_day=1, is_active=True,
            description=None, service_url=None, creation_date=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, handler, mocks):
        user = self._make_user()
        account = self._make_account()
        category = Category(id=1, name="Streaming", type="EXPENSE")
        subscription = self._make_subscription()

        mocks["user_repo"].get_by_id = AsyncMock(return_value=user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["category_repo"].get_by_id = AsyncMock(return_value=category)
        mocks["subscription_repo"].create = AsyncMock(return_value=subscription)

        dto = CreateSubscriptionDTO(
            user_id=1, account_uuid="acc-uuid-1", category_id=1,
            name="Netflix", amount=Decimal("199.00"), frequency=Frequency.MONTHLY,
            start_date=date.today(), billing_day=1,
        )
        command = CreateSubscriptionCommand(dto=dto)
        result = await handler.handle(command)

        assert result.name == "Netflix"
        assert result.account_uuid == "acc-uuid-1"
        mocks["subscription_repo"].create.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_user_not_found(self, handler, mocks):
        mocks["user_repo"].get_by_id = AsyncMock(return_value=None)

        dto = CreateSubscriptionDTO(
            user_id=99, account_uuid="acc-uuid-1", category_id=1, name="Netflix",
            amount=Decimal("199.00"), frequency=Frequency.MONTHLY,
            start_date=date.today(), billing_day=1,
        )
        with pytest.raises(UserNotFoundError):
            await handler.handle(CreateSubscriptionCommand(dto=dto))

    @pytest.mark.asyncio
    async def test_raises_user_inactive(self, handler, mocks):
        mocks["user_repo"].get_by_id = AsyncMock(return_value=self._make_user(is_active=False))

        dto = CreateSubscriptionDTO(
            user_id=1, account_uuid="acc-uuid-1", category_id=1, name="Netflix",
            amount=Decimal("199.00"), frequency=Frequency.MONTHLY,
            start_date=date.today(), billing_day=1,
        )
        with pytest.raises(UserNotFoundError):
            await handler.handle(CreateSubscriptionCommand(dto=dto))

    @pytest.mark.asyncio
    async def test_raises_account_not_found(self, handler, mocks):
        mocks["user_repo"].get_by_id = AsyncMock(return_value=self._make_user())
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        dto = CreateSubscriptionDTO(
            user_id=1, account_uuid="fake-uuid", category_id=1, name="Netflix",
            amount=Decimal("199.00"), frequency=Frequency.MONTHLY,
            start_date=date.today(), billing_day=1,
        )
        with pytest.raises(AccountNotFoundError):
            await handler.handle(CreateSubscriptionCommand(dto=dto))

    @pytest.mark.asyncio
    async def test_creates_with_no_category(self, handler, mocks):
        user = self._make_user()
        account = self._make_account()
        subscription = self._make_subscription()
        subscription.category_id = None

        mocks["user_repo"].get_by_id = AsyncMock(return_value=user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["subscription_repo"].create = AsyncMock(return_value=subscription)

        dto = CreateSubscriptionDTO(
            user_id=1, account_uuid="acc-uuid-1", category_id=None,
            name="Netflix", amount=Decimal("199.00"), frequency=Frequency.MONTHLY,
            start_date=date.today(), billing_day=1,
        )
        result = await handler.handle(CreateSubscriptionCommand(dto=dto))

        assert result is not None
        mocks["category_repo"].get_by_id.assert_not_called()
