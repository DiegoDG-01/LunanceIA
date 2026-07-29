"""Unit tests for RecurringIncome entity."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from domain.entities.recurring_income import RecurringIncome
from domain.objects.enums import Frequency
from domain.objects.money import Money
from shared.exceptions.domain import InvalidIncomeDateRangeError


def make_income(**overrides) -> RecurringIncome:
    """Build a valid recurring income, overriding only what the test needs."""
    defaults = {
        "user_id": 1,
        "account_id": 1,
        "category_id": 1,
        "name": "Nómina",
        "amount": Money(Decimal("15000.00")),
        "frequency": Frequency.MONTHLY,
        "start_date": date(2026, 1, 15),
    }
    defaults.update(overrides)
    return RecurringIncome.create_new(**defaults)


@pytest.mark.unit
class TestRecurringIncomeCreation:
    """Test RecurringIncome.create_new defaults and validation."""

    def test_create_new_sets_defaults(self):
        income = make_income()

        assert income.id is None
        assert income.uuid is None
        assert income.is_active is True
        assert income.end_date is None
        assert income.description is None

    def test_create_new_defaults_next_payment_to_start_date(self):
        income = make_income(start_date=date(2026, 3, 1))

        assert income.next_payment_date == date(2026, 3, 1)

    def test_create_new_respects_explicit_next_payment_date(self):
        income = make_income(
            start_date=date(2026, 1, 1), next_payment_date=date(2026, 1, 15)
        )

        assert income.next_payment_date == date(2026, 1, 15)

    def test_create_new_sets_utc_creation_date(self):
        income = make_income()

        assert isinstance(income.creation_date, datetime)
        assert income.creation_date.tzinfo == timezone.utc

    def test_create_new_rejects_end_date_before_start_date(self):
        with pytest.raises(InvalidIncomeDateRangeError):
            make_income(start_date=date(2026, 7, 15), end_date=date(2026, 1, 1))

    def test_create_new_allows_end_date_equal_to_start_date(self):
        income = make_income(start_date=date(2026, 7, 15), end_date=date(2026, 7, 15))

        assert income.end_date == date(2026, 7, 15)


@pytest.mark.unit
class TestRecurringIncomeIsDue:
    """Test RecurringIncome.is_due."""

    TODAY = date(2026, 7, 15)

    def test_due_when_payment_date_is_in_the_past(self):
        income = make_income(next_payment_date=date(2026, 7, 1))

        assert income.is_due(self.TODAY) is True

    def test_due_when_payment_date_is_today(self):
        income = make_income(next_payment_date=self.TODAY)

        assert income.is_due(self.TODAY) is True

    def test_not_due_when_payment_date_is_in_the_future(self):
        income = make_income(next_payment_date=date(2026, 8, 1))

        assert income.is_due(self.TODAY) is False

    def test_not_due_when_inactive(self):
        income = make_income(next_payment_date=date(2026, 7, 1))
        income.deactivate()

        assert income.is_due(self.TODAY) is False

    def test_not_due_when_next_payment_is_beyond_end_date(self):
        income = make_income(
            next_payment_date=date(2026, 7, 12), end_date=date(2026, 7, 10)
        )

        assert income.is_due(self.TODAY) is False

    def test_due_when_pending_payment_falls_within_ended_contract(self):
        """Un periodo ganado dentro del contrato se paga aunque el contrato ya terminó."""
        income = make_income(
            next_payment_date=date(2026, 7, 1), end_date=date(2026, 7, 10)
        )

        assert income.is_due(self.TODAY) is True

    def test_due_when_end_date_is_today(self):
        income = make_income(next_payment_date=self.TODAY, end_date=self.TODAY)

        assert income.is_due(self.TODAY) is True


@pytest.mark.unit
class TestRecurringIncomeAdvanceNextPayment:
    """Test RecurringIncome.advance_next_payment date math."""

    def test_monthly_day_31_reanchors_after_short_months(self):
        """Golden case: payroll on the 31st survives February without degrading."""
        income = make_income(frequency=Frequency.MONTHLY, start_date=date(2026, 1, 31))

        expected = [
            date(2026, 2, 28),
            date(2026, 3, 31),
            date(2026, 4, 30),
            date(2026, 5, 31),
        ]
        for expected_date in expected:
            income.advance_next_payment()
            assert income.next_payment_date == expected_date

    def test_biweekly_advances_exactly_14_days(self):
        income = make_income(frequency=Frequency.BIWEEKLY, start_date=date(2026, 7, 3))

        income.advance_next_payment()

        assert income.next_payment_date == date(2026, 7, 17)

    def test_weekly_advances_7_days(self):
        income = make_income(frequency=Frequency.WEEKLY, start_date=date(2026, 7, 3))

        income.advance_next_payment()

        assert income.next_payment_date == date(2026, 7, 10)

    def test_daily_advances_1_day(self):
        income = make_income(frequency=Frequency.DAILY, start_date=date(2026, 7, 3))

        income.advance_next_payment()

        assert income.next_payment_date == date(2026, 7, 4)

    def test_bimonthly_advances_2_months(self):
        income = make_income(
            frequency=Frequency.BIMONTHLY, start_date=date(2026, 1, 15)
        )

        income.advance_next_payment()

        assert income.next_payment_date == date(2026, 3, 15)

    def test_quarterly_advances_3_months(self):
        income = make_income(
            frequency=Frequency.QUARTERLY, start_date=date(2026, 1, 15)
        )

        income.advance_next_payment()

        assert income.next_payment_date == date(2026, 4, 15)

    def test_semi_annual_advances_6_months(self):
        income = make_income(
            frequency=Frequency.SEMI_ANNUAL, start_date=date(2026, 1, 15)
        )

        income.advance_next_payment()

        assert income.next_payment_date == date(2026, 7, 15)

    def test_annual_advances_1_year(self):
        income = make_income(frequency=Frequency.ANNUAL, start_date=date(2026, 1, 15))

        income.advance_next_payment()

        assert income.next_payment_date == date(2027, 1, 15)

    def test_annual_on_leap_day_falls_back_to_feb_28(self):
        income = make_income(frequency=Frequency.ANNUAL, start_date=date(2028, 2, 29))

        income.advance_next_payment()
        assert income.next_payment_date == date(2029, 2, 28)

        income.advance_next_payment()
        assert income.next_payment_date == date(2030, 2, 28)


@pytest.mark.unit
class TestRecurringIncomeStatus:
    """Test activate/deactivate."""

    def test_deactivate_and_activate(self):
        income = make_income()

        income.deactivate()
        assert income.is_active is False

        income.activate()
        assert income.is_active is True
