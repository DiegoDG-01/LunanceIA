from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from domain.entities.user import User
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.schemas.responses.category import (
    CategoryResponse,
    CategoryListResponse,
)
from presentation.dependencies.service_deps import get_categories_handler
from application.queries.get_categories_query import (
    GetCategoriesQuery,
    GetCategoriesHandler,
)


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=CategoryListResponse)
@limiter.limit("50/minute")
async def get_categories(
    request: Request,
    only_active: bool = True,
    current_user: User = Depends(get_current_active_user),
    handler: GetCategoriesHandler = Depends(get_categories_handler),
):
    query = GetCategoriesQuery(only_active=only_active)

    categories = await handler.handle(query)

    return CategoryListResponse(
        categories=[CategoryResponse(**category.__dict__) for category in categories],
        total=len(categories),
    )
