import os
import random
from datetime import date, timedelta
from decimal import Decimal

from locust import HttpUser, between, task

AUTH_TOKEN = os.environ.get("LOCUST_AUTH_TOKEN", "")

API_PREFIX = "/api/v2"


class LunanceUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        self.account_uuids: list[str] = []
        self.investment_uuids: list[str] = []
        self.category_ids: list[int] = list(range(1, 6))
        if not AUTH_TOKEN:
            raise ValueError(
                "LOCUST_AUTH_TOKEN environment variable is required. "
                "Set it with a valid JWT token."
            )
        self.client.headers.update({"Authorization": f"Bearer {AUTH_TOKEN}"})

    # --- Auth (weight 1) ---

    @task(1)
    def get_me(self):
        self.client.get(f"{API_PREFIX}/auth/me", name="/auth/me")

    # --- Accounts (weight 3) ---

    @task(3)
    def list_accounts(self):
        self.client.get(f"{API_PREFIX}/account/", name="/account/ [GET]")

    @task(1)
    def get_account(self):
        if not self.account_uuids:
            return
        uuid = random.choice(self.account_uuids)
        self.client.get(
            f"{API_PREFIX}/account/{uuid}", name="/account/{uuid} [GET]"
        )

    @task(1)
    def create_account(self):
        account_types = ["CHECKING", "SAVINGS"]
        currencies = ["MXN", "USD"]

        payload = {
            "bank_id": random.randint(1, 21),
            "name": f"Stress Test Account {random.randint(1, 100_000)}",
            "account_type": random.choice(account_types),
            "initial_balance": float(Decimal(random.uniform(100, 50_000)).quantize(Decimal("0.01"))),
            "currency": random.choice(currencies),
            "is_active": True,
        }

        with self.client.post(
            f"{API_PREFIX}/account/",
            json=payload,
            name="/account/ [POST]",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                account_uuid = data.get("account_uuid")
                if account_uuid:
                    self.account_uuids.append(account_uuid)
                response.success()
            else:
                response.failure(f"Status {response.status_code}: {response.text}")

    # --- Transactions (weight 5) ---

    @task(5)
    def list_transactions(self):
        self.client.get(
            f"{API_PREFIX}/transaction/",
            params={"limit": 20},
            name="/transaction/ [GET]",
        )

    @task(2)
    def create_transaction(self):
        if not self.account_uuids:
            return

        transaction_types = ["INCOME", "EXPENSE"]
        payload = {
            "account_uuid": random.choice(self.account_uuids),
            "transaction_type": random.choice(transaction_types),
            "amount": float(Decimal(random.uniform(1, 5_000)).quantize(Decimal("0.01"))),
            "description": f"Stress test transaction {random.randint(1, 100_000)}",
        }
        if self.category_ids:
            payload["category_id"] = random.choice(self.category_ids)

        self.client.post(
            f"{API_PREFIX}/transaction/",
            json=payload,
            name="/transaction/ [POST]",
        )

    # --- Investments (weight 5) ---

    @task(2)
    def create_investment_account(self):
        maturity = date.today() + timedelta(days=random.randint(90, 730))
        lock_end = date.today() + timedelta(days=random.randint(30, 365))

        payload = {
            "bank_id": random.randint(1, 21),
            "name": f"Stress Investment {random.randint(1, 100_000)}",
            "account_type": "INVESTMENT",
            "initial_balance": float(Decimal(random.uniform(1_000, 500_000)).quantize(Decimal("0.01"))),
            "currency": "MXN",
            "is_active": True,
            "investment_settings": {
                "investment_type": random.choice(["fixed_term", "stocks", "bonds", "mutual_fund", "etf", "other"]),
                "interest_rate": float(Decimal(random.uniform(4, 15)).quantize(Decimal("0.01"))),
                "lock_period_end_date": lock_end.isoformat(),
                "maturity_date": maturity.isoformat(),
                "early_withdrawal_penalty": float(Decimal(random.uniform(0, 5)).quantize(Decimal("0.01"))),
            },
        }

        with self.client.post(
            f"{API_PREFIX}/account/",
            json=payload,
            name="/account/ [POST investment]",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                account_uuid = data.get("account_uuid")
                if account_uuid:
                    self.account_uuids.append(account_uuid)
                    self.investment_uuids.append(account_uuid)
                response.success()
            else:
                response.failure(f"Status {response.status_code}: {response.text}")

    @task(5)
    def get_investment_yields(self):
        if not self.investment_uuids:
            return
        uuid = random.choice(self.investment_uuids)
        self.client.get(
            f"{API_PREFIX}/investments/{uuid}/yields/",
            params={"limit": random.choice([30, 90, 365])},
            name="/investments/{uuid}/yields/",
        )

    @task(5)
    def get_investment_projections(self):
        if not self.investment_uuids:
            return
        uuid = random.choice(self.investment_uuids)
        self.client.get(
            f"{API_PREFIX}/investments/{uuid}/projections/",
            params={"days": random.choice([30, 90, 180, 365])},
            name="/investments/{uuid}/projections/",
        )

    # --- Dashboard (weight 3) ---

    @task(3)
    def get_dashboard(self):
        self.client.get(f"{API_PREFIX}/dashboard/", name="/dashboard/ [GET]")

    # --- Subscriptions (weight 2) ---

    @task(2)
    def list_subscriptions(self):
        self.client.get(
            f"{API_PREFIX}/subscription/", name="/subscription/ [GET]"
        )
