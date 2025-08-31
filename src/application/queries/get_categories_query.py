from dataclasses import dataclass
from typing import List

from domain.repositories.category_repository import CategoryRepository
from application.dto.category_dto import CategoryResponseDTO


@dataclass
class GetCategoriesQuery:
    only_active: bool = True


class GetCategoriesHandler:
    def __init__(self, category_repository: CategoryRepository):
        self.category_repository = category_repository

    async def handle(self, query: GetCategoriesQuery) -> List[CategoryResponseDTO]:
        categories = await self.category_repository.get_all()

        if query.only_active:
            categories = [category for category in categories if category.is_active]

        return [CategoryResponseDTO.from_entity(category) for category in categories]
