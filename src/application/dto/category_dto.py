from dataclasses import dataclass
from typing import Optional
from domain.entities.category import Category


@dataclass
class CategoryResponseDTO:
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    is_active: bool
    type: Optional[str]

    @classmethod
    def from_entity(cls, category: Category) -> "CategoryResponseDTO":
        return cls(
            id=category.id,
            name=category.name,
            description=category.description,
            icon=category.icon,
            color=category.color,
            is_active=category.is_active,
            type=category.type,
        )
