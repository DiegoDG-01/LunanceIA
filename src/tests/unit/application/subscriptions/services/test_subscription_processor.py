import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from application.subscriptions.services.subscription_processor import (
    SubscriptionProcessor,
    MAX_CATCHUP_PERIODS,
)
from domain.entities.account import Account
from domain.entities.subscription import Subscription
from domain.entities.subscription_charge import SubscriptionCharge
from domain.entities.transaction import Transaction
from domain.objects.money import Money
from domain.objects.enums import AccountType, Frequency
from shared.exceptions.domain import AccountNotFoundError


def _make_subscription(
    next_charge_date: date,
    frequency: Frequency = Frequency.MONTHLY,
    billing_day=None,
    end_date=None,
    amount: str = "100.00",
) -> Subscription:
    sub = Subscription.create_new(
        user_id=10,
        account_id=20,
        category_id=5,
        name="Netflix",
        amount=Money(Decimal(amount)),
        frequency=frequency,
        start_date=next_charge_date,
        end_date=end_date,
        billing_day=billing_day,
        description=None,
        service_url=None,
        next_charge_date=next_charge_date,
    )
    sub.id = 1
    sub.uuid = "sub-123"
    return sub


@pytest.mark.unit
class TestSubscriptionProcessor:
    @pytest.fixture
    def mocks(self):
        return {
            "sub_repo": MagicMock(),
            "charge_repo": MagicMock(),
            "tx_repo": MagicMock(),
            "notification_repo": MagicMock(),
            "account_repo": MagicMock(),
        }

    @pytest.fixture
    def processor(self, mocks):
        return SubscriptionProcessor(
            mocks["sub_repo"],
            mocks["charge_repo"],
            mocks["tx_repo"],
            mocks["notification_repo"],
            mocks["account_repo"],
        )

    def _wire_happy_repos(self, mocks, account, existing_charge=None):
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock(return_value=account)
        mocks["charge_repo"].get_by_subscription_and_date = AsyncMock(
            return_value=existing_charge
        )
        saved_charge = MagicMock(spec=SubscriptionCharge)
        saved_charge.id = 500
        mocks["charge_repo"].create = AsyncMock(return_value=saved_charge)
        mocks["charge_repo"].update = AsyncMock()
        mock_tx = MagicMock(spec=Transaction)
        mock_tx.id = 100
        mocks["tx_repo"].create = AsyncMock(return_value=mock_tx)
        mocks["sub_repo"].update = AsyncMock()
        mocks["notification_repo"].create = AsyncMock()
        return saved_charge

    def _make_account(self, balance: str = "1000.00") -> Account:
        account = Account.create_new(
            user_id=10,
            bank_id=1,
            name="Cuenta Test",
            account_type=AccountType.CHECKING,
            initial_balance=Money(Decimal(balance)),
        )
        account.id = 20
        return account

    # --- _create_charge -----------------------------------------------------

    async def test_create_charge_happy_path(self, processor, mocks):
        account = self._make_account("1000.00")
        saved_charge = self._wire_happy_repos(mocks, account)
        sub = _make_subscription(date.today(), amount="199.00")

        result = await processor._create_charge(sub, date.today())

        assert result is True
        mocks["charge_repo"].create.assert_called_once()
        mocks["tx_repo"].create.assert_called_once()
        saved_charge.mark_as_paid.assert_called_once_with(100)
        mocks["charge_repo"].update.assert_called_once_with(saved_charge)
        mocks["account_repo"].update.assert_called_once_with(account)
        assert account.current_balance.amount == Decimal("801.00")
        mocks["account_repo"].get_by_id.assert_awaited_once_with(
            sub.account_id, for_update=True
        )

    async def test_create_charge_uses_charge_date_not_today(self, processor, mocks):
        account = self._make_account()
        self._wire_happy_repos(mocks, account)
        sub = _make_subscription(date.today())
        past = date.today() - timedelta(days=5)

        await processor._create_charge(sub, past)

        created_charge = mocks["charge_repo"].create.call_args.args[0]
        assert created_charge.charge_date == past
        created_tx = mocks["tx_repo"].create.call_args.args[0]
        assert created_tx.transaction_date == past

    async def test_create_charge_idempotent_when_charge_exists(self, processor, mocks):
        account = self._make_account("1000.00")
        self._wire_happy_repos(mocks, account, existing_charge=MagicMock())
        sub = _make_subscription(date.today())

        result = await processor._create_charge(sub, date.today())

        assert result is False
        mocks["charge_repo"].create.assert_not_called()
        mocks["tx_repo"].create.assert_not_called()
        assert account.current_balance.amount == Decimal("1000.00")

    async def test_create_charge_account_not_found(self, processor, mocks):
        mocks["account_repo"].get_by_id = AsyncMock(return_value=None)
        mocks["charge_repo"].get_by_subscription_and_date = AsyncMock(return_value=None)
        mocks["charge_repo"].create = AsyncMock()
        mocks["tx_repo"].create = AsyncMock()
        sub = _make_subscription(date.today())

        with pytest.raises(AccountNotFoundError):
            await processor._create_charge(sub, date.today())

        mocks["charge_repo"].create.assert_not_called()
        mocks["tx_repo"].create.assert_not_called()

    # --- _process_subscription (catch-up) -----------------------------------

    async def test_process_subscription_recovers_missed_periods(self, processor, mocks):
        account = self._make_account("1000.00")
        self._wire_happy_repos(mocks, account)
        first_of_month = date.today().replace(day=1)
        start = first_of_month - relativedelta(months=2)
        sub = _make_subscription(start, frequency=Frequency.MONTHLY, billing_day=1)

        created = await processor._process_subscription(sub, date.today())

        assert created == 3  # dos meses atrás + el actual
        assert sub.next_charge_date > date.today()
        mocks["sub_repo"].update.assert_awaited_once_with(sub)
        mocks["notification_repo"].create.assert_awaited_once()

    async def test_process_subscription_nothing_due(self, processor, mocks):
        account = self._make_account()
        self._wire_happy_repos(mocks, account)
        future = date.today() + timedelta(days=10)
        sub = _make_subscription(future)

        created = await processor._process_subscription(sub, date.today())

        assert created == 0
        mocks["charge_repo"].create.assert_not_called()
        mocks["notification_repo"].create.assert_not_called()
        mocks["sub_repo"].update.assert_awaited_once_with(sub)

    async def test_process_subscription_respects_catchup_cap(self, processor, mocks):
        account = self._make_account("100000.00")
        self._wire_happy_repos(mocks, account)
        start = date.today() - timedelta(days=730)
        sub = _make_subscription(start, frequency=Frequency.DAILY, amount="1.00")

        created = await processor._process_subscription(sub, date.today())

        assert created == MAX_CATCHUP_PERIODS

    async def test_process_subscription_stops_at_end_date(self, processor, mocks):
        account = self._make_account()
        self._wire_happy_repos(mocks, account)
        start = date.today() - timedelta(days=40)
        end = date.today() - timedelta(days=20)
        sub = _make_subscription(
            start, frequency=Frequency.DAILY, end_date=end, amount="1.00"
        )

        created = await processor._process_subscription(sub, date.today())

        # sólo cobra hasta end_date (21 días: start .. end inclusive)
        assert created == 21

    @pytest.mark.parametrize(
        "frequency",
        [
            Frequency.DAILY,
            Frequency.WEEKLY,
            Frequency.BIWEEKLY,
            Frequency.MONTHLY,
            Frequency.BIMONTHLY,
            Frequency.QUARTERLY,
            Frequency.SEMI_ANNUAL,
            Frequency.ANNUAL,
        ],
    )
    async def test_process_subscription_single_due_each_frequency(
        self, processor, mocks, frequency
    ):
        account = self._make_account("100000.00")
        self._wire_happy_repos(mocks, account)
        sub = _make_subscription(date.today(), frequency=frequency, amount="1.00")

        created = await processor._process_subscription(sub, date.today())

        assert created == 1
        assert sub.next_charge_date > date.today()

    # --- process_due_subscriptions (agregación) -----------------------------

    async def test_process_due_aggregates_stats(self, processor, mocks):
        sub1 = _make_subscription(date.today())
        sub1.uuid = "sub-1"
        sub2 = _make_subscription(date.today())
        sub2.uuid = "sub-2"
        mocks["sub_repo"].get_due_subscriptions = AsyncMock(return_value=[sub1, sub2])

        async def fake_process(sub, today):
            return 2 if sub.uuid == "sub-1" else 0

        with patch.object(
            processor, "_process_subscription", side_effect=fake_process
        ):
            stats = await processor.process_due_subscriptions()

        assert stats["processed"] == 2
        assert stats["created"] == 2
        assert stats["skipped"] == 1
        assert stats["failed"] == 0

    async def test_process_due_isolates_failures(self, processor, mocks):
        sub1 = _make_subscription(date.today())
        sub1.uuid = "sub-1"
        sub2 = _make_subscription(date.today())
        sub2.uuid = "sub-2"
        mocks["sub_repo"].get_due_subscriptions = AsyncMock(return_value=[sub1, sub2])

        async def fake_process(sub, today):
            if sub.uuid == "sub-1":
                raise RuntimeError("boom")
            return 1

        with patch.object(
            processor, "_process_subscription", side_effect=fake_process
        ):
            stats = await processor.process_due_subscriptions()

        assert stats["processed"] == 2
        assert stats["failed"] == 1
        assert stats["created"] == 1
