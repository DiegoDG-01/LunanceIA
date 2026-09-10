from fastapi import APIRouter, Depends, Request

from application.categories.queries.get_categories import (
    GetCategoriesHandler,
    GetCategoriesQuery,
)
from domain.entities.user import User
from domain.objects.enums import APIKeyScope
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_50_per_minute,
)
from presentation.dependencies import get_categories_handler
from presentation.dependencies.auth_deps import require_scope
from presentation.schemas.responses.category import (
    CategoryListResponse,
    CategoryResponse,
)

router = APIRouter()


@router.get("/", response_model=CategoryListResponse)
async def get_categories(
    request: Request,
    only_active: bool = True,
    current_user: User = Depends(require_scope(APIKeyScope.CATEGORIES_READ.value)),
    handler: GetCategoriesHandler = Depends(get_categories_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetCategoriesQuery(only_active=only_active)

    categories = await handler.handle(query)

    return CategoryListResponse(
        categories=[CategoryResponse(**category.__dict__) for category in categories],
        total=len(categories),
    )
