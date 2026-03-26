from fastapi import Depends
from application.ai.queries.analyze_image import AnalyzeImageHandler
from infrastructure.database.repositories.sqlalchemy_category_repository import SQLAlchemyCategoryRepository
from presentation.dependencies.repositories import get_category_repository


def get_analyze_image_handler(
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> AnalyzeImageHandler:
    return AnalyzeImageHandler(category_repo)