"""Cuentas en USD y EUR: el dinero se mueve en la moneda de su cuenta.

Movimientos, transferencias, apartados, suscripciones, ingresos recurrentes y MSI. Entre
cuentas de monedas distintas no se mueve nada (409).

Cada rechazo es la última llamada de su prueba: la sesión que comparten las pruebas no
sobrevive al rollback de un error.
"""

from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

import httpx
import pytest

from infrastructure.scheduler import jobs

from ..conftest import AuthTokens
from ..idempotency import with_idempotency_key

TODAY = str(date.today())


class Api:
    def __init__(self, client: httpx.AsyncClient, tokens: AuthTokens):
        self.client = client
        self.tokens = tokens

    @property
    def headers(self) -> dict:
        return self.tokens.get_auth_headers()

    async def post(self, path: str, body: dict) -> httpx.Response:
        return await self.client.post(
            path, json=body, headers=with_idempotency_key(self.headers)
        )

    async def get(self, path: str, **params) -> httpx.Response:
        return await self.client.get(path, params=params, headers=self.headers)

    async def account(
        self, currency: str, balance=1000, kind="CHECKING", **extra
    ) -> str:
        response = await self.post(
            "/account",
            {
                "name": f"{kind} {currency}",
                "account_type": kind,
                "bank_id": 1,
                "initial_balance": balance,
                "currency": currency,
                **extra,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["account_uuid"]

    async def balance(self, account_uuid: str) -> tuple[Decimal, str]:
        body = (await self.get(f"/account/{account_uuid}")).json()
        return Decimal(str(body["current_balance"])), body["currency"]


@pytest.fixture
def api(http_client, auth_tokens) -> Api:
    return Api(http_client, auth_tokens)


def _expense(account_uuid: str, amount, **extra) -> dict:
    return {
        "account_uuid": account_uuid,
        "category_id": 1,
        "transaction_type": "EXPENSE",
        "amount": amount,
        "transaction_date": TODAY,
        **extra,
    }


@pytest.mark.e2e
@pytest.mark.asyncio
class TestTransactions:
    @pytest.mark.parametrize("currency", ["USD", "EUR"])
    async def test_expense_and_income_move_the_account_in_its_currency(
        self, api: Api, currency
    ):
        account = await api.account(currency)
        expense = await api.post("/transaction", _expense(account, 100))
        assert expense.status_code == 200, expense.text
        assert expense.json()["currency"] == currency
        income = await api.post(
            "/transaction",
            {**_expense(account, 40), "transaction_type": "INCOME"},
        )
        assert income.status_code == 200, income.text
        assert await api.balance(account) == (Decimal("940.00"), currency)

        listed = (await api.get("/transaction", account_uuid=account)).json()
        assert {t["currency"] for t in listed} == {currency}

    async def test_edit_and_delete_in_dollars(self, api: Api):
        account = await api.account("USD")
        created = (await api.post("/transaction", _expense(account, 100))).json()

        edited = await api.client.put(
            f"/transaction/{created['uuid']}/", json={"amount": 30}, headers=api.headers
        )
        assert edited.status_code == 200, edited.text
        assert await api.balance(account) == (Decimal("970.00"), "USD")

        deleted = await api.client.delete(
            f"/transaction/{created['uuid']}/", headers=api.headers
        )
        assert deleted.status_code in (200, 204), deleted.text
        assert await api.balance(account) == (Decimal("1000.00"), "USD")

    async def test_cannot_move_to_an_account_in_another_currency(self, api: Api):
        dollars = await api.account("USD")
        pesos = await api.account("MXN")
        created = (await api.post("/transaction", _expense(dollars, 100))).json()

        response = await api.client.put(
            f"/transaction/{created['uuid']}/",
            json={"account_uuid": pesos},
            headers=api.headers,
        )
        assert response.status_code == 409, response.text
        assert response.json()["error_code"] == "ACCOUNT_CURRENCY_MISMATCH"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestTransfers:
    async def test_between_accounts_in_the_same_currency(self, api: Api):
        source, destination = await api.account("EUR"), await api.account("EUR", 0)
        response = await api.post(
            "/transfers/",
            {
                "source_account_uuid": source,
                "destination_account_uuid": destination,
                "amount": 250,
                "transfer_date": TODAY,
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["currency"] == "EUR"
        assert await api.balance(source) == (Decimal("750.00"), "EUR")
        assert await api.balance(destination) == (Decimal("250.00"), "EUR")

        deleted = await api.client.delete(
            f"/transfers/{response.json()['transfer_uuid']}", headers=api.headers
        )
        assert deleted.status_code in (200, 204), deleted.text
        assert await api.balance(source) == (Decimal("1000.00"), "EUR")

    async def test_between_currencies_is_rejected(self, api: Api):
        pesos, dollars = await api.account("MXN"), await api.account("USD")
        response = await api.post(
            "/transfers/",
            {
                "source_account_uuid": pesos,
                "destination_account_uuid": dollars,
                "amount": 100,
                "transfer_date": TODAY,
            },
        )
        assert response.status_code == 409, response.text
        assert response.json()["error_code"] == "TRANSFER_CURRENCY_MISMATCH"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPositions:
    async def test_position_takes_the_account_currency(self, api: Api):
        account = await api.account("EUR")
        body = {
            "account_uuid": account,
            "name": "Apartado",
            "position_type": "ON_DEMAND",
            "amount": 300,
            "annual_rate": 5,
        }
        created = await api.post("/positions/", body)
        assert created.status_code == 201, created.text
        position = created.json()
        assert position["currency"] == "EUR"

        deposit = await api.post(
            f"/positions/{position['position_uuid']}/deposit/",
            {"amount": 100, "currency": "eur"},
        )
        assert deposit.status_code == 200, deposit.text
        withdraw = await api.post(
            f"/positions/{position['position_uuid']}/withdraw/", {"amount": 50}
        )
        assert withdraw.status_code == 200, withdraw.text
        assert await api.balance(account) == (Decimal("650.00"), "EUR")

    async def test_another_currency_is_rejected(self, api: Api):
        account = await api.account("USD")
        response = await api.post(
            "/positions/",
            {
                "account_uuid": account,
                "name": "Apartado",
                "position_type": "ON_DEMAND",
                "amount": 100,
                "annual_rate": 5,
                "currency": "MXN",
            },
        )
        assert response.status_code == 409, response.text
        assert response.json()["error_code"] == "ACCOUNT_CURRENCY_MISMATCH"


@pytest.fixture
def job_session(monkeypatch, db_session):
    """Los jobs abren su propia sesión: aquí usan la de la prueba."""

    @asynccontextmanager
    async def session():
        yield db_session

    monkeypatch.setattr(jobs, "AsyncSessionLocal", session)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestScheduledMoney:
    async def test_subscription_is_charged_in_dollars(self, api: Api, job_session):
        account = await api.account("USD")
        created = await api.post(
            "/subscription",
            {
                "account_uuid": account,
                "category_id": 1,
                "name": "Servidor",
                "amount": 20,
                "frequency": "MONTHLY",
                "start_date": TODAY,
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["currency"] == "USD"

        await jobs.process_subscriptions_job()

        assert await api.balance(account) == (Decimal("980.00"), "USD")

    async def test_recurring_income_is_deposited_in_euros(self, api: Api, job_session):
        account = await api.account("EUR")
        created = await api.post(
            "/incomes",
            {
                "account_uuid": account,
                "category_id": 1,
                "name": "Renta",
                "amount": 500,
                "frequency": "MONTHLY",
                "start_date": TODAY,
                "next_payment_date": TODAY,
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["currency"] == "EUR"

        await jobs.process_recurring_income_job()

        assert await api.balance(account) == (Decimal("1500.00"), "EUR")
        deposits = await api.get(f"/incomes/{created.json()['uuid']}/deposits")
        assert {d["currency"] for d in deposits.json()} == {"EUR"}

    async def test_subscription_cannot_move_to_another_currency(self, api: Api):
        dollars, pesos = await api.account("USD"), await api.account("MXN")
        created = await api.post(
            "/subscription",
            {
                "account_uuid": dollars,
                "category_id": 1,
                "name": "Servidor",
                "amount": 20,
                "frequency": "MONTHLY",
                "start_date": TODAY,
            },
        )
        response = await api.client.patch(
            f"/subscription/{created.json()['uuid']}/",
            json={"account_uuid": pesos},
            headers=api.headers,
        )
        assert response.status_code == 409, response.text
        assert response.json()["error_code"] == "ACCOUNT_CURRENCY_MISMATCH"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestInstallments:
    async def _card(self, api: Api, currency: str) -> str:
        # Como en el resto de las pruebas de MSI, la tarjeta arranca con saldo a favor.
        return await api.account(
            currency,
            10000,
            "CREDIT_CARD",
            credit_card_settings={
                "billing_cycle_day": 15,
                "payment_due_day": 5,
                "credit_limit": 10000,
                "minimum_payment_percentage": 5,
            },
        )

    async def test_purchase_and_payment_in_dollars(self, api: Api):
        card = await self._card(api, "USD")
        purchase = await api.post(
            "/installments/",
            {
                "account_uuid": card,
                "category_id": 1,
                "description": "Laptop",
                "total_amount": 1200,
                "num_installments": 12,
                "installment_type": "NO_INTEREST",
                "annual_interest_rate": 0,
                "purchase_date": TODAY,
            },
        )
        assert purchase.status_code == 200, purchase.text
        assert purchase.json()["currency"] == "USD"
        assert await api.balance(card) == (Decimal("8800.00"), "USD")
        first_charge = purchase.json()["charges"][0]["uuid"]

        dollars = await api.account("USD")
        paid = await api.post(
            f"/installments/{first_charge}/pay/",
            {"source_account_uuid": dollars, "payment_date": TODAY},
        )
        assert paid.status_code == 200, paid.text
        assert await api.balance(dollars) == (Decimal("900.00"), "USD")
        assert await api.balance(card) == (Decimal("8900.00"), "USD")

        # Pagar la siguiente desde pesos: sería una transferencia entre monedas.
        pesos = await api.account("MXN")
        second_charge = purchase.json()["charges"][1]["uuid"]
        rejected = await api.post(
            f"/installments/{second_charge}/pay/",
            {"source_account_uuid": pesos, "payment_date": TODAY},
        )
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["error_code"] == "TRANSFER_CURRENCY_MISMATCH"
