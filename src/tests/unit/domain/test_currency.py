"""Solo MXN, USD y EUR: la lista única y dónde se exige."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from domain.entities.accounts.account import Account
from domain.entities.investments.investment_position import InvestmentPosition
from domain.objects.enums import AccountType, Currency, PositionType
from domain.objects.money import Money, ensure_supported_currency
from shared.constants.business import SUPPORTED_CURRENCIES
from shared.exceptions.domain import InvalidCurrencyError
from shared.utils.validations import validate_currency_code


@pytest.mark.unit
class TestSupportedCurrencies:
    def test_one_list_everywhere(self):
        assert set(SUPPORTED_CURRENCIES) == {c.value for c in Currency}
        assert set(SUPPORTED_CURRENCIES) == {"MXN", "USD", "EUR"}

    @pytest.mark.parametrize("currency", ["MXN", "USD", "EUR"])
    def test_supported(self, currency):
        ensure_supported_currency(currency)

    @pytest.mark.parametrize("currency", ["GBP", "usd", "zzz", ""])
    def test_unsupported(self, currency):
        with pytest.raises(InvalidCurrencyError):
            ensure_supported_currency(currency)

    def test_helper_ignores_case(self):
        assert validate_currency_code("eur")
        assert not validate_currency_code("GBP")

    def test_money_still_accepts_other_currencies(self):
        # Los precios de valores pueden venir en otra moneda.
        assert Money(Decimal(1), "GBP").currency == "GBP"


@pytest.mark.unit
class TestEntitiesRequireSupportedCurrency:
    def test_account(self):
        with pytest.raises(InvalidCurrencyError):
            Account.create_new(
                user_id=1,
                bank_id=1,
                name="Libras",
                account_type=AccountType.CHECKING,
                initial_balance=Money(Decimal(10), "GBP"),
            )

    def test_account_defaults_to_pesos(self):
        account = Account.create_new(
            user_id=1, bank_id=1, name="Pesos", account_type=AccountType.CHECKING
        )
        assert account.current_balance.currency == "MXN"

    def test_position(self):
        with pytest.raises(InvalidCurrencyError):
            InvestmentPosition.create_new(
                account_id=1,
                name="Apartado",
                position_type=PositionType.ON_DEMAND,
                initial_balance=Money(Decimal(10), "GBP"),
                annual_rate=Decimal(5),
                start_date=datetime.now(UTC).date(),
            )
