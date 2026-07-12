import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import date
from application.subscriptions.services.subscription_processor import SubscriptionProcessor
from domain.entities.account import Account
from domain.entities.subscription import Subscription
from domain.entities.subscription_charge import SubscriptionCharge
from domain.entities.transaction import Transaction
from domain.objects.money import Money
from domain.objects.enums import AccountType
from shared.exceptions.domain import AccountNotFoundError
from decimal import Decimal

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
            "db": AsyncMock()
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

    async def test_should_generate_transaction_true(self, processor, mocks):
        today = date.today()
        sub = MagicMock(spec=Subscription)
        sub.id = 1
        sub.uuid = "sub-123"
        sub.billing_day = today.day
        sub.end_date = None

        mocks["charge_repo"].get_by_subscription_and_month = AsyncMock(return_value=None)

        result = await processor._should_generate_transaction(sub)
        assert result is True

    async def test_should_generate_transaction_false_wrong_day(self, processor, mocks):
        today = date.today()
        sub = MagicMock(spec=Subscription)
        sub.id = 1
        sub.uuid = "sub-123"
        sub.billing_day = today.day + 1 if today.day < 28 else 1
        sub.end_date = None

        result = await processor._should_generate_transaction(sub)
        assert result is False

    async def test_should_generate_transaction_false_already_charged(self, processor, mocks):
        today = date.today()
        sub = MagicMock(spec=Subscription)
        sub.id = 1
        sub.uuid = "sub-123"
        sub.billing_day = today.day
        sub.end_date = None

        mocks["charge_repo"].get_by_subscription_and_month = AsyncMock(return_value=MagicMock())

        result = await processor._should_generate_transaction(sub)
        assert result is False

    async def test_create_transaction_from_subscription(self, processor, mocks):
        sub = MagicMock(spec=Subscription)
        sub.id = 1
        sub.uuid = "sub-123"
        sub.user_id = 10
        sub.account_id = 20
        sub.category_id = 5
        sub.name = "Netflix"
        sub.amount = Money(Decimal("199.00"))

        account = Account.create_new(
            user_id=10,
            bank_id=1,
            name="Cuenta Test",
            account_type=AccountType.CHECKING,
            initial_balance=Money(Decimal("1000.00")),
        )
        account.id = 20
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock(return_value=account)

        mock_charge = MagicMock(spec=SubscriptionCharge)
        mock_charge.id = 500
        mocks["charge_repo"].create = AsyncMock(return_value=mock_charge)

        mock_tx = MagicMock(spec=Transaction)
        mock_tx.id = 100
        mocks["tx_repo"].create = AsyncMock(return_value=mock_tx)

        mocks["charge_repo"].update = AsyncMock()

        await processor._create_transaction_from_subscription(sub)

        mocks["charge_repo"].create.assert_called_once()
        mocks["tx_repo"].create.assert_called_once()
        mock_charge.mark_as_paid.assert_called_once_with(100)
        mocks["charge_repo"].update.assert_called_once_with(mock_charge)
        mocks["account_repo"].update.assert_called_once_with(account)
        assert account.current_balance.amount == Decimal("801.00")

    async def test_create_transaction_account_not_found(self, processor, mocks):
        sub = MagicMock(spec=Subscription)
        sub.id = 1
        sub.uuid = "sub-123"
        sub.user_id = 10
        sub.account_id = 20
        sub.category_id = 5
        sub.name = "Netflix"
        sub.amount = Money(Decimal("199.00"))

        mocks["account_repo"].get_by_id = AsyncMock(return_value=None)
        mocks["charge_repo"].create = AsyncMock()
        mocks["tx_repo"].create = AsyncMock()

        with pytest.raises(AccountNotFoundError):
            await processor._create_transaction_from_subscription(sub)

        mocks["charge_repo"].create.assert_not_called()
        mocks["tx_repo"].create.assert_not_called()

    async def test_process_due_subscriptions_integration(self, processor, mocks):
        today = date.today()

        sub1 = MagicMock(spec=Subscription)
        sub1.id = 1
        sub1.uuid = "sub-1"
        sub1.billing_day = today.day
        sub1.end_date = None

        sub2 = MagicMock(spec=Subscription)
        sub2.id = 2
        sub2.uuid = "sub-2"
        sub2.billing_day = today.day + 1
        sub2.end_date = None

        mocks["sub_repo"].get_active_subscriptions = AsyncMock(return_value=[sub1, sub2])
        mocks["db"].commit = AsyncMock()

        # Mocking should_generate_transaction to control the flow
        async def mock_should_generate(s):
            return s.uuid == "sub-1"

        with patch.object(processor, '_should_generate_transaction', side_effect=mock_should_generate):
            with patch.object(processor, '_create_transaction_from_subscription', new=AsyncMock()) as mock_create:
                stats = await processor.process_due_subscriptions()

                assert stats["processed"] == 2
                assert stats["created"] == 1
                assert stats["skipped"] == 1
                mock_create.assert_called_once_with(sub1)
