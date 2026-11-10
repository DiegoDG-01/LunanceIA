from pydantic import BaseModel


class CategoryResponse(BaseModel):
    id: int
    name: str
    type: str
    description: str | None
    color: str | None
    icon: str | None
    is_active: bool

    class config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    categories: list[CategoryResponse]
    total: int
