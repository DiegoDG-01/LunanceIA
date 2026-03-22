import os

from pydantic_ai import Agent
from domain.entities.expense_suggestion import ExpenseAnalysis
from infrastructure.config.settings import settings

os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY

agent = Agent(
    model=f"google-gla:{settings.GEMINI_MODEL_ID}",
    result_type=ExpenseAnalysis,
    system_prompt=(
        "Eres un asesor financiero personal. "
        "Analiza los gastos mensuales del usuario y devuelve sugerencias concretas "
        "para optimizar su presupuesto. Sé específico y práctico."
    ),
)
