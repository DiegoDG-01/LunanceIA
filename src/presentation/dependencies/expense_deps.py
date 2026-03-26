from fastapi import Depends
from application.ai.queries.expense_advisor import GetExpenseAdvisorHandler
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from presentation.dependencies.repositories import get_transaction_repository


def get_expense_advisor_handler(
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
) -> GetExpenseAdvisorHandler:
    return GetExpenseAdvisorHandler(transaction_repo)
