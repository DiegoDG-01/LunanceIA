from fastapi import APIRouter, Request, Depends

from domain.entities.user import User
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.schemas.responses.category import (
    CategoryResponse,
    CategoryListResponse,
)
from presentation.dependencies import get_categories_handler
from application.categories.queries.get_categories import (
    GetCategoriesQuery,
    GetCategoriesHandler,
)


from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_50_per_minute,
)

router = APIRouter()


@router.get("/", response_model=CategoryListResponse)
async def get_categories(
    request: Request,
    only_active: bool = True,
    current_user: User = Depends(get_current_active_user),
    handler: GetCategoriesHandler = Depends(get_categories_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetCategoriesQuery(only_active=only_active)

    categories = await handler.handle(query)

    return CategoryListResponse(
        categories=[CategoryResponse(**category.__dict__) for category in categories],
        total=len(categories),
    )
