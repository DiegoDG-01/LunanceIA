from dataclasses import dataclass
from pydantic_ai import BinaryContent
from application.ai.schemas.image_analysis import ImageAnalysis
from domain.repositories.category_repository import CategoryRepository
from infrastructure.external_services.agents.image import image_agent as agent


@dataclass
class AnalyzeImageQuery:
    image_data: bytes
    mime_type: str = "image/jpeg"


class AnalyzeImageHandler:
    def __init__(
        self,
        category_repository: CategoryRepository,
    ):
        self.category_repository = category_repository

    async def handle(self, query: AnalyzeImageQuery) -> ImageAnalysis:
        result = await agent.run(
            [BinaryContent(data=query.image_data, media_type=query.mime_type)],
        )

        analysis = result.data

        if analysis.category:
            category = await self.category_repository.get_by_name(
                analysis.category.value
            )
            analysis.category_id = category.id if category else None

        return analysis
