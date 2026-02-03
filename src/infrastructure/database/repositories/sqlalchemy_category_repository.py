from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.repositories.category_repository import CategoryRepository
from domain.entities.category import Category
from shared.exceptions.domain import CategoryNotFoundError
from infrastructure.database.models.category import CategoryModel


class SQLAlchemyCategoryRepository(CategoryRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    def _model_to_entity(self, model: CategoryModel) -> Category:
        return Category(
            id=model.id,
            name=model.name,
            type=model.type,
            description=model.description,
            color=model.color,
            icon=model.icon,
            is_active=model.is_active,
        )

    async def get_all(self) -> List[Category]:
        stmt = select(CategoryModel)
        result = await self.db.execute(stmt)
        category_models = result.scalars().all()

        return [self._model_to_entity(model) for model in category_models]

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        category_model = await self.db.get(CategoryModel, category_id)
        if category_model:
            return self._model_to_entity(category_model)
        return None

    async def create(self, category: Category) -> Category:
        category_model = CategoryModel(
            name=category.name,
            description=category.description,
            color=category.color,
            icon=category.icon,
            is_active=category.is_active,
            type=category.type,
        )

        self.db.add(category_model)
        await self.db.commit()
        await self.db.refresh(category_model)

        return self._model_to_entity(category_model)

    async def update(self, category: Category) -> Category:
        category_model = await self.db.get(CategoryModel, category.id)
        if not category_model:
            raise CategoryNotFoundError(category.id)

        category_model.name = category.name
        category_model.description = category.description
        category_model.color = category.color
        category_model.icon = category.icon
        category_model.is_active = category.is_active

        await self.db.commit()
        await self.db.refresh(category_model)

        return self._model_to_entity(category_model)

    async def delete(self, category_id: int) -> None:
        category_model = await self.db.get(CategoryModel, category_id)
        if not category_model:
            raise CategoryNotFoundError(category_id)

        await self.db.delete(category_model)
        await self.db.commit()
