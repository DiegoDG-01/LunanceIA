from dataclasses import dataclass


@dataclass
class Category:
    id: int
    name: str
    type: str | None = None
    is_active: bool = True
    description: str | None = None
    icon: str | None = None
    color: str | None = None

    @classmethod
    def create_new(
        cls,
        name: str,
        description: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        is_active: bool = True,
        type: str | None = None,
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
