import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import date, timedelta
from application.subscriptions.services.subscription_processor import SubscriptionProcessor
from domain.entities.subscription import Subscription
from domain.entities.subscription_charge import SubscriptionCharge
from domain.entities.transaction import Transaction
from domain.objects.money import Money
from domain.objects.enums import TransactionType, Frequency
from decimal import Decimal

@pytest.mark.unit
class TestSubscriptionProcessor:
    @pytest.fixture
    def mocks(self):
        return {
            "sub_repo": MagicMock(),
            "charge_repo": MagicMock(),
            "tx_repo": MagicMock(),
            "db": MagicMock()
        }

    @pytest.fixture
    def processor(self, mocks):
        return SubscriptionProcessor(
            mocks["sub_repo"],
            mocks["charge_repo"],
            mocks["tx_repo"]
        )

    def test_should_generate_transaction_true(self, processor, mocks):
        today = date.today()
        sub = MagicMock(spec=Subscription)
        sub.id = 1
        sub.uuid = "sub-123"
        sub.billing_day = today.day
        sub.end_date = None

        mocks["charge_repo"].get_by_subscription_and_month.return_value = None

        result = processor._should_generate_transaction(sub, mocks["db"])
        assert result is True

    def test_should_generate_transaction_false_wrong_day(self, processor, mocks):
        today = date.today()
        sub = MagicMock(spec=Subscription)
        sub.id = 1
        sub.uuid = "sub-123"
        sub.billing_day = today.day + 1 if today.day < 28 else 1
        sub.end_date = None

        result = processor._should_generate_transaction(sub, mocks["db"])
        assert result is False

    def test_should_generate_transaction_false_already_charged(self, processor, mocks):
        today = date.today()
        sub = MagicMock(spec=Subscription)
        sub.id = 1
        sub.uuid = "sub-123"
        sub.billing_day = today.day
        sub.end_date = None

        mocks["charge_repo"].get_by_subscription_and_month.return_value = MagicMock()

        result = processor._should_generate_transaction(sub, mocks["db"])
        assert result is False

    def test_create_transaction_from_subscription(self, processor, mocks):
        sub = MagicMock(spec=Subscription)
        sub.id = 1
        sub.uuid = "sub-123"
        sub.user_id = 10
        sub.account_id = 20
        sub.category_id = 5
        sub.name = "Netflix"
        sub.amount = Money(Decimal("199.00"))

        mock_charge = MagicMock(spec=SubscriptionCharge)
        mock_charge.id = 500
        mocks["charge_repo"].create.return_value = mock_charge

        mock_tx = MagicMock(spec=Transaction)
        mock_tx.id = 100
        mocks["tx_repo"].create.return_value = mock_tx

        processor._create_transaction_from_subscription(sub, mocks["db"])

        mocks["charge_repo"].create.assert_called_once()
        mocks["tx_repo"].create.assert_called_once()
        mock_charge.mark_as_paid.assert_called_once_with(100)
        mocks["charge_repo"].update.assert_called_once_with(mock_charge)

    def test_process_due_subscriptions_integration(self, processor, mocks):
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

        mocks["sub_repo"].get_active_subscriptions.return_value = [sub1, sub2]

        # Mocking should_generate_transaction to control the flow
        with patch.object(processor, '_should_generate_transaction') as mock_should:
            mock_should.side_effect = lambda s, db: s.uuid == "sub-1"

            with patch.object(processor, '_create_transaction_from_subscription') as mock_create:
                stats = processor.process_due_subscriptions(mocks["db"])

                assert stats["processed"] == 2
                assert stats["created"] == 1
                assert stats["skipped"] == 1
                mock_create.assert_called_once_with(sub1, mocks["db"])
