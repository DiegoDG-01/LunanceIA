"""El asesor de gastos recibe los montos agrupados por moneda."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

import pytest

from application.ai.queries.expense_advisor import (
    GetExpenseAdvisorHandler,
    GetExpenseAdvisorQuery,
)
from domain.entities.transactions.transaction import Transaction
from domain.objects.enums import TransactionType
from domain.objects.money import Money
from domain.repositories.transactions.transaction_repository import (
    TransactionRepository,
)


def _movement(amount: str, currency: str, description: str):
    transaction = Transaction.create_new(
        user_id=1,
        account_id=1,
        category_id=1,
        transaction_type=TransactionType.EXPENSE,
        amount=Money(Decimal(amount), currency),
        transaction_date=date(2026, 11, 3),
        description=description,
    )
    return transaction, "Cuenta", None, "uuid", "Alimentos"


class _Repository:
    async def get_by_date_range(self, user_id, start_date, end_date):
        return [
            _movement("200", "MXN", "Súper"),
            _movement("15", "USD", "Café en Austin"),
        ]


class _Agent:
    def __init__(self):
        self.prompts: list[str] = []

    async def run(self, prompt):
        self.prompts.append(prompt)
        return SimpleNamespace(output="análisis")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prompt_groups_amounts_by_currency():
    agent = _Agent()
    handler = GetExpenseAdvisorHandler(
        transaction_repository=cast(TransactionRepository, _Repository()),
        agent=agent,
    )

    assert await handler.handle(GetExpenseAdvisorQuery(user_id=1)) == "análisis"

    [prompt] = agent.prompts
    assert "no sumes" in prompt
    assert "'MXN': [{'category': 'Alimentos', 'amount': 200.0" in prompt
    assert "'USD': [{'category': 'Alimentos', 'amount': 15.0" in prompt
    assert "son pesos" not in prompt
