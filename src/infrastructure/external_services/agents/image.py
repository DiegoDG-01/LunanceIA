import os

from pydantic_ai import Agent
from domain.entities.image_analysis import ImageAnalysis
from infrastructure.config.settings import settings
from shared.utils.prompts import IMAGE_ANALYZE_PROMPT

os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY

image_agent = Agent(
    model=f"google-gla:{settings.GEMINI_MODEL_ID}",
    result_type=ImageAnalysis,
    system_prompt=IMAGE_ANALYZE_PROMPT,
)
