import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime, timezone
from typing import Optional
from decimal import Decimal

from application.subscriptions.queries.get_last_transactions import (
    GetLastTransactionsQuery,
    GetLastTransactionsHandler,
)
from domain.entities.subscription import Subscription
from domain.entities.subscription_charge import SubscriptionCharge
from domain.objects.enums import Frequency, TransactionStatus
from domain.objects.money import Money
from shared.exceptions.domain import SubscriptionNotFoundError


@pytest.mark.unit
class TestGetLastTransactionsHandler:
    @pytest.fixture
    def mocks(self):
        return {
            "subscription_repo": MagicMock(),
            "subscription_charge_repo": MagicMock(),
        }

    @pytest.fixture
    def handler(self, mocks):
        return GetLastTransactionsHandler(
            subscription_repository=mocks["subscription_repo"],
            subscription_charge_repository=mocks["subscription_charge_repo"],
        )

    def _make_subscription(self, sub_id: int = 1, uuid: str = "sub-uuid-1") -> Subscription:
        return Subscription(
            id=sub_id,
            uuid=uuid,
            user_id=1,
            account_id=10,
            category_id=2,
            name="Netflix",
            amount=Money(Decimal("199.00")),
            frequency=Frequency.MONTHLY,
            start_date=date(2025, 1, 1),
            end_date=None,
            billing_day=1,
            is_active=True,
            description=None,
            service_url=None,
            creation_date=datetime.now(timezone.utc),
        )

    def _make_charge(
        self,
        charge_id: int = 1,
        sub_id: int = 1,
        amount: str = "199.00",
        processing_date: Optional[datetime] = None,
    ) -> SubscriptionCharge:
        charge = SubscriptionCharge(
            id=charge_id,
            uuid=f"charge-uuid-{charge_id}",
            subscription_id=sub_id,
            charge_date=date(2026, 2, 1),
            amount=Money(Decimal(amount)),
            status=TransactionStatus.PAGADO,
            transaction_id=charge_id * 10,
            processing_date=processing_date or datetime(2026, 2, 1, 12, 0, 0),
        )
        return charge

    @pytest.mark.asyncio
    async def test_returns_list_of_last_transactions(self, handler, mocks):
        subscription = self._make_subscription()
        charge1 = self._make_charge(1, processing_date=datetime(2026, 2, 1, 12, 0))
        charge2 = self._make_charge(2, amount="199.00", processing_date=datetime(2026, 1, 1, 12, 0))

        last_charges = [
            (charge1, "Netflix", "BBVA Débito"),
            (charge2, "Netflix", "BBVA Débito"),
        ]

        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=subscription)
        mocks["subscription_charge_repo"].get_last_charges_by_subscription_id = AsyncMock(
            return_value=last_charges
        )

        query = GetLastTransactionsQuery(user_id=1, subscription_uuid="sub-uuid-1")
        result = await handler.handle(query)

        assert len(result) == 2
        assert result[0].name == "Netflix"
        assert result[0].account_name == "BBVA Débito"
        assert result[0].amount == Decimal("199.00")
        assert result[0].charge_date == date(2026, 2, 1)

        mocks["subscription_repo"].get_by_uuid_and_user_id.assert_called_once_with(
            "sub-uuid-1", 1
        )
        mocks["subscription_charge_repo"].get_last_charges_by_subscription_id.assert_called_once_with(
            subscription_id=subscription.id
        )

    @pytest.mark.asyncio
    async def test_raises_when_subscription_not_found(self, handler, mocks):
        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        query = GetLastTransactionsQuery(user_id=1, subscription_uuid="nonexistent-uuid")

        with pytest.raises(SubscriptionNotFoundError):
            await handler.handle(query)

        mocks["subscription_charge_repo"].get_last_charges_by_subscription_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_charges(self, handler, mocks):
        subscription = self._make_subscription()

        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=subscription)
        mocks["subscription_charge_repo"].get_last_charges_by_subscription_id = AsyncMock(
            return_value=[]
        )

        query = GetLastTransactionsQuery(user_id=1, subscription_uuid="sub-uuid-1")
        result = await handler.handle(query)

        assert result == []

    @pytest.mark.asyncio
    async def test_maps_charge_date_from_processing_date(self, handler, mocks):
        subscription = self._make_subscription()
        processing_dt = datetime(2026, 3, 5, 8, 30, 0)
        charge = self._make_charge(1, processing_date=processing_dt)

        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=subscription)
        mocks["subscription_charge_repo"].get_last_charges_by_subscription_id = AsyncMock(
            return_value=[(charge, "Spotify", "Santander")]
        )

        query = GetLastTransactionsQuery(user_id=1, subscription_uuid="sub-uuid-1")
        result = await handler.handle(query)

        assert len(result) == 1
        assert result[0].charge_date == date(2026, 3, 5)
        assert result[0].name == "Spotify"
        assert result[0].account_name == "Santander"

    @pytest.mark.asyncio
    async def test_uses_correct_subscription_id_for_charges_query(self, handler, mocks):
        subscription = self._make_subscription(sub_id=42)
        charge = self._make_charge(1)

        mocks["subscription_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=subscription)
        mocks["subscription_charge_repo"].get_last_charges_by_subscription_id = AsyncMock(
            return_value=[(charge, "Netflix", "BBVA")]
        )

        query = GetLastTransactionsQuery(user_id=1, subscription_uuid="sub-uuid-1")
        await handler.handle(query)

        mocks["subscription_charge_repo"].get_last_charges_by_subscription_id.assert_called_once_with(
            subscription_id=42
        )
