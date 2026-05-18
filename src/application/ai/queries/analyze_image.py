from dataclasses import dataclass
from io import BytesIO
from PIL import Image

from PIL import UnidentifiedImageError
from application.interfaces.uploaded_file import UploadedFileInterface
from pydantic_ai import BinaryContent
from application.ai.schemas.image_analysis import ImageAnalysis
from application.interfaces.ai_agent import AIAgentInterface
from domain.repositories.category_repository import CategoryRepository
from pydantic_ai.exceptions import UnexpectedModelBehavior, ModelHTTPError
from shared.exceptions.domain import (
    AIInvalidResponseError,
    AIServiceError,
    InvalidImageError,
)


@dataclass
class AnalyzeImageQuery:
    file: UploadedFileInterface


class AnalyzeImageHandler:
    def __init__(
        self,
        category_repository: CategoryRepository,
        agent: AIAgentInterface,
    ):
        self.category_repository = category_repository
        self.agent = agent

    async def handle(self, query: AnalyzeImageQuery) -> ImageAnalysis:
        MAX_IMAGE_BYTES = 2 * 1024 * 1024
        ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
        MAX_IMAGE_WIDTH = 4096
        MAX_IMAGE_HEIGHT = 4096

        file = query.file
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise InvalidImageError(f"Invalid image type: {file.content_type}")

        image_data = await file.read(MAX_IMAGE_BYTES + 1)
        if len(image_data) > MAX_IMAGE_BYTES:
            raise InvalidImageError("Image is too large")

        try:
            with Image.open(BytesIO(image_data)) as img:
                img.verify()

            with Image.open(BytesIO(image_data)) as img:
                width, height = img.size
        except UnidentifiedImageError:
            raise InvalidImageError("This is not a valid image file")

        if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
            raise InvalidImageError("Image dimensions not allowed")

        try:
            result = await self.agent.run(
                [BinaryContent(data=image_data, media_type=file.content_type)],
            )
        except UnexpectedModelBehavior:
            raise AIInvalidResponseError()
        except ModelHTTPError as err:
            raise AIServiceError(f"Error to communicate with the AI model {err}")

        analysis = result.output

        if analysis.category:
            category = await self.category_repository.get_by_name(
                analysis.category.value
            )
            analysis.category_id = category.id if category else None

        return analysis
