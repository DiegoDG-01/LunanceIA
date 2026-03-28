from dataclasses import dataclass
from datetime import date
from application.ai.schemas.expense_analysis import ExpenseAnalysis
from application.interfaces.ai_agent import AIAgentInterface
from domain.repositories.transaction_repository import TransactionRepository
from shared.exceptions.domain import TransactionNotActivityError


@dataclass
class GetExpenseAdvisorQuery:
    user_id: int


class GetExpenseAdvisorHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        agent: AIAgentInterface,
    ):
        self.transaction_repository = transaction_repository
        self.agent = agent

    async def handle(self, query: GetExpenseAdvisorQuery) -> ExpenseAnalysis:
        transactions = await self.transaction_repository.get_by_date_range(
            query.user_id,
            start_date=date.today().replace(day=1),
            end_date=date.today(),
        )

        if not transactions:
            raise TransactionNotActivityError()

        expense_summary = [
            {
                "category": category_name,
                "amount": float(t.amount.amount),
                "type": t.transaction_type.value,
                "description": t.description,
            }
            for t, _, _, _, category_name in transactions
        ]

        prompt = f"Analiza estos gastos del mes: {expense_summary}"
        result = await self.agent.run(prompt)

        return result.data
