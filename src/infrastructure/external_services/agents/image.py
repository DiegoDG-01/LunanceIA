from pydantic_ai import Agent
from application.ai.schemas.image_analysis import ImageAnalysis
from infrastructure.external_services.agents.model_factory import build_model
from shared.utils.prompts import IMAGE_ANALYZE_PROMPT

image_agent = Agent(
    model=build_model(),
    output_type=ImageAnalysis,
    system_prompt=IMAGE_ANALYZE_PROMPT,
)
