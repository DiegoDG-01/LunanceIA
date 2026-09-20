from fastapi import Depends

from application.ai.queries.analyze_image import AnalyzeImageHandler
from application.ai.queries.expense_advisor import GetExpenseAdvisorHandler
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from infrastructure.external_services.agents.expense import expense_agent
from infrastructure.external_services.agents.image import image_agent
from presentation.dependencies import get_transaction_repository
from presentation.dependencies.repositories import get_category_repository


def get_analyze_image_handler(
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> AnalyzeImageHandler:
    return AnalyzeImageHandler(category_repo, image_agent)


def get_expense_advisor_handler(
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
) -> GetExpenseAdvisorHandler:
    return GetExpenseAdvisorHandler(transaction_repo, expense_agent)
