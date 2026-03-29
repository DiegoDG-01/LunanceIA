from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.category import Category


class CategoryRepository(ABC):
    @abstractmethod
    async def get_all(self) -> List[Category]:
        pass

    @abstractmethod
    async def get_by_id(self, category_id: int) -> Optional[Category]:
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
    async def get_by_name(self, category_name: str) -> Optional[Category]:
        pass
