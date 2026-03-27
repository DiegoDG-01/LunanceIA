import os

from pydantic_ai import Agent
from application.ai.schemas.expense_analysis import ExpenseAnalysis
from infrastructure.config.settings import settings
from shared.utils.prompts import EXPENSE_ADVISOR_PROMPT

os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY

expense_agent = Agent(
    model=f"google-gla:{settings.GEMINI_MODEL_ID}",
    result_type=ExpenseAnalysis,
    system_prompt=EXPENSE_ADVISOR_PROMPT,
)
