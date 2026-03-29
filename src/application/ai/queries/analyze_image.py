from dataclasses import dataclass
from pydantic_ai import BinaryContent
from application.ai.schemas.image_analysis import ImageAnalysis
from application.interfaces.ai_agent import AIAgentInterface
from domain.repositories.category_repository import CategoryRepository


@dataclass
class AnalyzeImageQuery:
    image_data: bytes
    mime_type: str = "image/jpeg"


class AnalyzeImageHandler:
    def __init__(
        self,
        category_repository: CategoryRepository,
        agent: AIAgentInterface,
    ):
        self.category_repository = category_repository
        self.agent = agent

    async def handle(self, query: AnalyzeImageQuery) -> ImageAnalysis:
        result = await self.agent.run(
            [BinaryContent(data=query.image_data, media_type=query.mime_type)],
        )

        analysis = result.output

        if analysis.category:
            category = await self.category_repository.get_by_name(
                analysis.category.value
            )
            analysis.category_id = category.id if category else None

        return analysis
