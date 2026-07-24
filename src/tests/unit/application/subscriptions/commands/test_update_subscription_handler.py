import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta

from application.subscriptions.commands.update_subscription import (
    UpdateSubscriptionCommand,
    UpdateSubscriptionHandler,
)
from application.dto.subscription_dto import UpdateSubscriptionDTO
from domain.entities.account import Account
from domain.entities.category import Category
from domain.entities.subscription import Subscription
from domain.objects.enums import AccountType, Frequency
from domain.objects.money import Money
from shared.exceptions.domain import (
    SubscriptionNotFoundError,
    InvalidSubscriptionDateRangeError,
)


@pytest.mark.unit
class TestUpdateSubscriptionHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "subscription_repo": MagicMock(),
            "category_repo": MagicMock(),
            "account_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return UpdateSubscriptionHandler(
            subscription_repository=mocks["subscription_repo"],
            category_repository=mocks["category_repo"],
            account_repository=mocks["account_repo"],
            uow=mocks["uow"],
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

    def _make_subscription(
        self, frequency=Frequency.MONTHLY, start_date=None, next_charge_date=None
    ) -> Subscription:
        start = start_date or date(2026, 1, 15)
        return Subscription(
            id=1, uuid="sub-uuid-1", user_id=1, account_id=10, category_id=1,
            name="Netflix", amount=Money(Decimal("199.00")),
            frequency=frequency, start_date=start,
            end_date=None, billing_day=15,
            next_charge_date=next_charge_date or date(2026, 3, 15),
            is_active=True, description=None, service_url=None,
            creation_date=datetime.now(timezone.utc),
        )

    def _wire(self, mocks, subscription):
        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=subscription
        )
        mocks["subscription_repo"].update = AsyncMock(side_effect=lambda s: s)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=self._make_account())
        mocks["category_repo"].get_by_id = AsyncMock(
            return_value=Category(id=1, name="Streaming", type="EXPENSE")
        )

    async def test_not_found_raises(self, handler, mocks):
        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=None
        )
        cmd = UpdateSubscriptionCommand(
            subscription_uuid="missing", user_id=1,
            dto=UpdateSubscriptionDTO(name="New"),
        )
        with pytest.raises(SubscriptionNotFoundError):
            await handler.handle(cmd)

    async def test_editing_name_does_not_touch_schedule(self, handler, mocks):
        sub = self._make_subscription()
        original = sub.next_charge_date
        self._wire(mocks, sub)

        cmd = UpdateSubscriptionCommand(
            subscription_uuid="sub-uuid-1", user_id=1,
            dto=UpdateSubscriptionDTO(name="Netflix Premium"),
        )
        await handler.handle(cmd)

        assert sub.name == "Netflix Premium"
        assert sub.next_charge_date == original  # agenda intacta

    async def test_changing_frequency_reschedules(self, handler, mocks):
        # start en el pasado -> reschedule debe anclar a hoy, no al pasado
        sub = self._make_subscription(
            frequency=Frequency.MONTHLY,
            start_date=date.today() - relativedelta(months=6),
            next_charge_date=date.today() + timedelta(days=3),
        )
        self._wire(mocks, sub)

        cmd = UpdateSubscriptionCommand(
            subscription_uuid="sub-uuid-1", user_id=1,
            dto=UpdateSubscriptionDTO(frequency=Frequency.WEEKLY),
        )
        await handler.handle(cmd)

        assert sub.frequency == Frequency.WEEKLY
        # sin cobros retroactivos: la nueva fecha nunca queda en el pasado
        assert sub.next_charge_date >= date.today()

    async def test_changing_billing_day_reschedules(self, handler, mocks):
        sub = self._make_subscription(
            frequency=Frequency.MONTHLY,
            start_date=date.today() - relativedelta(months=2),
            next_charge_date=date.today() + timedelta(days=1),
        )
        self._wire(mocks, sub)
        before = sub.next_charge_date

        cmd = UpdateSubscriptionCommand(
            subscription_uuid="sub-uuid-1", user_id=1,
            dto=UpdateSubscriptionDTO(billing_day=28),
        )
        await handler.handle(cmd)

        assert sub.billing_day == 28
        assert sub.next_charge_date != before
        assert sub.next_charge_date >= date.today()

    async def test_toggling_active_does_not_reschedule(self, handler, mocks):
        sub = self._make_subscription()
        original = sub.next_charge_date
        self._wire(mocks, sub)

        cmd = UpdateSubscriptionCommand(
            subscription_uuid="sub-uuid-1", user_id=1,
            dto=UpdateSubscriptionDTO(is_active=False),
        )
        await handler.handle(cmd)

        assert sub.is_active is False
        assert sub.next_charge_date == original

    async def test_invalid_date_range_raises(self, handler, mocks):
        sub = self._make_subscription(
            start_date=date(2026, 6, 1), next_charge_date=date(2026, 6, 1)
        )
        self._wire(mocks, sub)

        cmd = UpdateSubscriptionCommand(
            subscription_uuid="sub-uuid-1", user_id=1,
            dto=UpdateSubscriptionDTO(end_date=date(2026, 1, 1)),
        )
        with pytest.raises(InvalidSubscriptionDateRangeError):
            await handler.handle(cmd)
