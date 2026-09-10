from abc import ABC, abstractmethod

from domain.entities.category import Category


class CategoryRepository(ABC):
    @abstractmethod
    async def get_all(self) -> list[Category]:
        pass

    @abstractmethod
    async def get_by_id(self, category_id: int) -> Category | None:
        pass

    @abstractmethod
    async def create(self, category: Category) -> Category:
        pass

    @abstractmethod
    async def update(self, category: Category) -> Category:
        pass

    @abstractmethod
    async def delete(self, category_id: int) -> None:
        pass

    @abstractmethod
    async def get_by_name(self, category_name: str) -> Category | None:
        pass
