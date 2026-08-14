"""Unit tests for InvestmentPosition entity."""

from datetime import date
from decimal import Decimal

import pytest

from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import (
    InterestType,
    MaturityAction,
    PositionStatus,
    PositionType,
)
from domain.objects.money import Money
from shared.exceptions.domain import (
    FixedTermDepositNotAllowedError,
    FixedTermWithdrawalNotAllowedError,
    InsufficientFundsError,
    InvalidFixedTermConfigError,
    InvalidInvestmentRateError,
    InvalidPenaltyPercentageError,
    InvestmentPositionLockedError,
    InvestmentPositionNotActiveError,
    InvestmentPositionNotMaturedError,
)


def make_position(**overrides) -> InvestmentPosition:
    """Build a valid on-demand position, overriding only what the test needs."""
    defaults = {
        "account_id": 1,
        "name": "Cajita vacaciones",
        "position_type": PositionType.ON_DEMAND,
        "initial_balance": Money(Decimal("1000.00")),
        "annual_rate": Decimal("10.00"),
        "start_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return InvestmentPosition.create_new(**defaults)


def make_fixed_term(**overrides) -> InvestmentPosition:
    """Build a valid fixed-term position."""
    defaults = {
        "position_type": PositionType.FIXED_TERM,
        "term_days": 90,
    }
    defaults.update(overrides)
    return make_position(**defaults)


@pytest.mark.unit
class TestInvestmentPositionCreation:
    """Test InvestmentPosition.create_new defaults and validation."""

    def test_create_new_sets_defaults(self):
        position = make_position()

        assert position.id is None
        assert position.uuid is None
        assert position.status == PositionStatus.ACTIVE
        assert position.accrued_yield.amount == Decimal(0)
        assert position.on_maturity == MaturityAction.HOLD
        assert position.base_principal is None

    def test_on_demand_ignores_term_fields(self):
        position = make_position(
            term_days=90,
            maturity_date=date(2026, 6, 1),
            lock_period_end_date=date(2026, 2, 1),
            early_withdrawal_penalty=Decimal("10.00"),
        )

        assert position.term_days is None
        assert position.maturity_date is None
        assert position.lock_period_end_date is None
        assert position.early_withdrawal_penalty is None

    def test_fixed_term_derives_maturity_from_term_days(self):
        position = make_fixed_term(term_days=90, start_date=date(2026, 1, 1))

        assert position.maturity_date == date(2026, 4, 1)

    def test_fixed_term_derives_term_days_from_maturity(self):
        position = make_fixed_term(
            term_days=None, maturity_date=date(2026, 1, 31), start_date=date(2026, 1, 1)
        )

        assert position.term_days == 30

    def test_fixed_term_without_term_raises(self):
        with pytest.raises(InvalidFixedTermConfigError):
            make_fixed_term(term_days=None, maturity_date=None)

    def test_fixed_term_with_past_maturity_raises(self):
        with pytest.raises(InvalidFixedTermConfigError):
            make_fixed_term(
                term_days=None,
                maturity_date=date(2025, 12, 1),
                start_date=date(2026, 1, 1),
            )

    def test_negative_rate_raises(self):
        with pytest.raises(InvalidInvestmentRateError):
            make_position(annual_rate=Decimal("-1.00"))

    def test_penalty_over_100_raises(self):
        with pytest.raises(InvalidPenaltyPercentageError):
            make_fixed_term(early_withdrawal_penalty=Decimal("150.00"))

    def test_simple_interest_sets_base_principal(self):
        position = make_position(interest_type=InterestType.SIMPLE)

        assert position.base_principal == Decimal("1000.00")


@pytest.mark.unit
class TestDepositAndWithdraw:
    """Test movement rules between available balance and the position."""

    def test_deposit_adds_to_balance(self):
        position = make_position()

        position.deposit(Money(Decimal("500.00")))

        assert position.balance.amount == Decimal("1500.00")

    def test_deposit_on_fixed_term_raises(self):
        position = make_fixed_term()

        with pytest.raises(FixedTermDepositNotAllowedError):
            position.deposit(Money(Decimal("500.00")))

    def test_withdraw_subtracts_from_balance(self):
        position = make_position()

        position.withdraw(Money(Decimal("400.00")))

        assert position.balance.amount == Decimal("600.00")

    def test_withdraw_more_than_balance_raises(self):
        position = make_position()

        with pytest.raises(InsufficientFundsError):
            position.withdraw(Money(Decimal("1000.01")))

    def test_withdraw_on_fixed_term_raises(self):
        position = make_fixed_term()

        with pytest.raises(FixedTermWithdrawalNotAllowedError):
            position.withdraw(Money(Decimal("100.00")))

    def test_operations_on_liquidated_position_raise(self):
        position = make_position()
        position.liquidate(date(2026, 2, 1))

        with pytest.raises(InvestmentPositionNotActiveError):
            position.deposit(Money(Decimal("100.00")))

    def test_simple_interest_deposit_grows_base_principal(self):
        position = make_position(interest_type=InterestType.SIMPLE)

        position.deposit(Money(Decimal("500.00")))

        assert position.base_principal == Decimal("1500.00")

    def test_simple_interest_withdraw_consumes_yield_before_capital(self):
        position = make_position(interest_type=InterestType.SIMPLE)
        position.accrue_yield(Money(Decimal("50.00")))

        position.withdraw(Money(Decimal("30.00")))
        assert position.base_principal == Decimal("1000.00")

        position.withdraw(Money(Decimal("100.00")))
        assert position.base_principal == Decimal("920.00")


@pytest.mark.unit
class TestAccrueYield:
    """Test where each position type places its daily yield."""

    def test_on_demand_capitalizes_into_balance(self):
        position = make_position()

        position.accrue_yield(Money(Decimal("1.25")))

        assert position.balance.amount == Decimal("1001.25")
        assert position.accrued_yield.amount == Decimal(0)

    def test_fixed_term_accrues_without_touching_balance(self):
        position = make_fixed_term()

        position.accrue_yield(Money(Decimal("1.25")))

        assert position.balance.amount == Decimal("1000.00")
        assert position.accrued_yield.amount == Decimal("1.25")
        assert position.total_value.amount == Decimal("1001.25")

    def test_accrue_on_matured_position_raises(self):
        position = make_fixed_term()
        position.mark_matured()

        with pytest.raises(InvestmentPositionNotActiveError):
            position.accrue_yield(Money(Decimal("1.25")))


@pytest.mark.unit
class TestMaturity:
    """Test maturity detection, HOLD state and renewal."""

    def test_is_due_for_maturity_on_and_after_date(self):
        position = make_fixed_term(term_days=90, start_date=date(2026, 1, 1))

        assert not position.is_due_for_maturity(date(2026, 3, 31))
        assert position.is_due_for_maturity(date(2026, 4, 1))
        assert position.is_due_for_maturity(date(2026, 4, 2))

    def test_on_demand_is_never_due(self):
        position = make_position()

        assert not position.is_due_for_maturity(date(2030, 1, 1))

    def test_mark_matured_stops_position(self):
        position = make_fixed_term()

        position.mark_matured()

        assert position.status == PositionStatus.MATURED

    def test_renew_reinvests_yield_for_same_term(self):
        position = make_fixed_term(term_days=90, start_date=date(2026, 1, 1))
        position.accrue_yield(Money(Decimal("25.00")))

        position.renew(date(2026, 4, 1))

        assert position.balance.amount == Decimal("1025.00")
        assert position.accrued_yield.amount == Decimal(0)
        assert position.start_date == date(2026, 4, 1)
        assert position.maturity_date == date(2026, 6, 30)
        assert position.status == PositionStatus.ACTIVE

    def test_renew_before_maturity_raises(self):
        position = make_fixed_term(term_days=90, start_date=date(2026, 1, 1))

        with pytest.raises(InvestmentPositionNotMaturedError):
            position.renew(date(2026, 2, 1))

    def test_renew_resets_simple_interest_base(self):
        position = make_fixed_term(
            term_days=90, start_date=date(2026, 1, 1), interest_type=InterestType.SIMPLE
        )
        position.accrue_yield(Money(Decimal("25.00")))

        position.renew(date(2026, 4, 1))

        assert position.base_principal == Decimal("1025.00")


@pytest.mark.unit
class TestLiquidate:
    """Test liquidation payouts, penalties and lock periods."""

    def test_on_demand_liquidation_pays_full_balance(self):
        position = make_position()
        position.accrue_yield(Money(Decimal("10.00")))

        payout = position.liquidate(date(2026, 2, 1))

        assert payout.amount == Decimal("1010.00")
        assert position.balance.amount == Decimal(0)
        assert position.status == PositionStatus.LIQUIDATED

    def test_matured_fixed_term_pays_capital_plus_yield(self):
        position = make_fixed_term(term_days=90, start_date=date(2026, 1, 1))
        position.accrue_yield(Money(Decimal("25.00")))
        position.mark_matured()

        payout = position.liquidate(date(2026, 4, 5))

        assert payout.amount == Decimal("1025.00")

    def test_early_liquidation_applies_penalty_on_yield_only(self):
        position = make_fixed_term(
            term_days=90,
            start_date=date(2026, 1, 1),
            early_withdrawal_penalty=Decimal("10.00"),
        )
        position.accrue_yield(Money(Decimal("100.00")))

        payout = position.liquidate(date(2026, 2, 1))

        # Capital intacto, rendimiento castigado 10%
        assert payout.amount == Decimal("1090.00")

    def test_early_liquidation_without_penalty_pays_full(self):
        position = make_fixed_term(term_days=90, start_date=date(2026, 1, 1))
        position.accrue_yield(Money(Decimal("100.00")))

        payout = position.liquidate(date(2026, 2, 1))

        assert payout.amount == Decimal("1100.00")

    def test_liquidation_during_lock_period_raises(self):
        position = make_fixed_term(
            term_days=90,
            start_date=date(2026, 1, 1),
            lock_period_end_date=date(2026, 2, 15),
        )

        with pytest.raises(InvestmentPositionLockedError):
            position.liquidate(date(2026, 2, 1))

    def test_liquidation_after_lock_period_is_allowed(self):
        position = make_fixed_term(
            term_days=90,
            start_date=date(2026, 1, 1),
            lock_period_end_date=date(2026, 2, 15),
        )

        payout = position.liquidate(date(2026, 2, 20))

        assert payout.amount == Decimal("1000.00")

    def test_liquidate_twice_raises(self):
        position = make_position()
        position.liquidate(date(2026, 2, 1))

        with pytest.raises(InvestmentPositionNotActiveError):
            position.liquidate(date(2026, 2, 2))
