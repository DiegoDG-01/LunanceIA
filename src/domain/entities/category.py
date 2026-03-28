from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    id: int
    name: str
    type: Optional[str] = None
    is_active: bool = True
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

    @classmethod
    def create_new(
        cls,
        name: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        is_active: bool = True,
        type: Optional[str] = None,
    ) -> "Category":
        if not name.strip():
            raise ValueError("Category name cannot be empty")

        return cls(
            id=0,
            name=name.strip(),
            description=description,
            icon=icon,
            color=color,
            is_active=is_active,
            type=type,
        )
