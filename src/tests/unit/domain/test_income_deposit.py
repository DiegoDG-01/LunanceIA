"""Unit tests for IncomeDeposit entity."""

from datetime import date, timezone
from decimal import Decimal

import pytest

from domain.entities.income_deposit import IncomeDeposit
from domain.objects.enums import TransactionStatus
from domain.objects.money import Money


def make_deposit() -> IncomeDeposit:
    return IncomeDeposit.create_pending(
        recurring_income_id=1,
        deposit_date=date(2026, 7, 15),
        amount=Money(Decimal("15000.00")),
    )


@pytest.mark.unit
class TestIncomeDeposit:
    """Test IncomeDeposit state machine."""

    def test_create_pending_initial_state(self):
        deposit = make_deposit()

        assert deposit.id is None
        assert deposit.uuid is None
        assert deposit.status == TransactionStatus.PENDIENTE
        assert deposit.transaction_id is None
        assert deposit.processing_date is None

    def test_mark_as_paid_links_transaction(self):
        deposit = make_deposit()

        deposit.mark_as_paid(transaction_id=100)

        assert deposit.status == TransactionStatus.PAGADO
        assert deposit.transaction_id == 100
        assert deposit.processing_date is not None
        assert deposit.processing_date.tzinfo == timezone.utc

    def test_mark_as_failed(self):
        deposit = make_deposit()

        deposit.mark_as_failed()

        assert deposit.status == TransactionStatus.FALLIDO
        assert deposit.transaction_id is None
        assert deposit.processing_date is not None

    def test_mark_as_cancelled(self):
        deposit = make_deposit()

        deposit.mark_as_cancelled()

        assert deposit.status == TransactionStatus.CANCELADO
        assert deposit.processing_date is not None
