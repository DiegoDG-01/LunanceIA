from dataclasses import dataclass

from domain.entities.category import Category


@dataclass
class CategoryResponseDTO:
    id: int
    name: str
    description: str | None
    icon: str | None
    color: str | None
    is_active: bool
    type: str | None

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
