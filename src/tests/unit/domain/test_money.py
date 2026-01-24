import pytest
from decimal import Decimal
from domain.objects.money import Money
from shared.exceptions.domain import (
    InsufficientFundsError,
    NegativeAmountError,
    CurrencyMismatchError
)

@pytest.mark.unit
class TestMoney:
    def test_money_creation_success(self):
        """Test creating Money object with valid amount and default currency."""
        money = Money(Decimal("100.00"))
        assert money.amount == Decimal("100.00")
        assert money.currency == "MXN"

    def test_money_creation_custom_currency(self):
        """Test creating Money object with custom currency."""
        money = Money(Decimal("50.00"), "USD")
        assert money.amount == Decimal("50.00")
        assert money.currency == "USD"

    def test_money_creation_negative_amount_fails(self):
        """Test that creating Money with negative amount raises NegativeAmountError."""
        with pytest.raises(NegativeAmountError, match="Cantidad negativa no permitida: -1.0"):
            Money(Decimal("-1.00"))

    def test_money_add_success(self):
        """Test adding two Money objects of same currency."""
        m1 = Money(Decimal("100.00"))
        m2 = Money(Decimal("50.00"))
        result = m1.add(m2)
        assert result.amount == Decimal("150.00")
        assert result.currency == "MXN"

    def test_money_add_different_currency_fails(self):
        """Test that adding Money with different currency raises CurrencyMismatchError."""
        m1 = Money(Decimal("100.00"), "MXN")
        m2 = Money(Decimal("50.00"), "USD")
        with pytest.raises(CurrencyMismatchError, match="Las monedas no coinciden: MXN vs USD"):
            m1.add(m2)

    def test_money_subtract_success(self):
        """Test subtracting two Money objects of same currency."""
        m1 = Money(Decimal("100.00"))
        m2 = Money(Decimal("40.00"))
        result = m1.subtract(m2)
        assert result.amount == Decimal("60.00")
        assert result.currency == "MXN"

    def test_money_subtract_different_currency_fails(self):
        """Test that subtracting Money with different currency raises CurrencyMismatchError."""
        m1 = Money(Decimal("100.00"), "MXN")
        m2 = Money(Decimal("50.00"), "USD")
        with pytest.raises(CurrencyMismatchError, match="Las monedas no coinciden: MXN vs USD"):
            m1.subtract(m2)

    def test_money_subtract_insufficient_funds_fails(self):
        """Test that subtracting more than available raises InsufficientFundsError."""
        m1 = Money(Decimal("50.00"))
        m2 = Money(Decimal("100.00"))
        with pytest.raises(InsufficientFundsError) as excinfo:
            m1.subtract(m2)

        assert excinfo.value.required_amount == 100.0
        assert excinfo.value.available_amount == 50.0

    def test_money_string_representation(self):
        """Test string representation of Money."""
        money = Money(Decimal("123.456"), "EUR")
        # Format is defined as f"{self.amount:.2f} {self.currency}"
        assert str(money) == "123.46 EUR"
