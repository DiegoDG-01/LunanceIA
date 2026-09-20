from pydantic_ai import Agent

from application.ai.schemas.expense_analysis import ExpenseAnalysis
from infrastructure.external_services.agents.model_factory import build_model
from shared.utils.prompts import EXPENSE_ADVISOR_PROMPT

expense_agent = Agent(
    model=build_model(),
    output_type=ExpenseAnalysis,
    system_prompt=EXPENSE_ADVISOR_PROMPT,
)
