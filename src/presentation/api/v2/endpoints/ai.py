from typing import cast

from fastapi import APIRouter, Depends, File, Request, UploadFile

from application.ai.queries.analyze_image import AnalyzeImageHandler, AnalyzeImageQuery
from application.ai.queries.expense_advisor import (
    GetExpenseAdvisorHandler,
    GetExpenseAdvisorQuery,
)
from application.ai.schemas.expense_analysis import ExpenseAnalysis
from application.ai.schemas.image_analysis import ImageAnalysis
from domain.entities.user import User
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_1_per_day,
)
from presentation.dependencies import (
    get_current_active_user,
    get_expense_advisor_handler,
)
from presentation.dependencies.ai_deps import get_analyze_image_handler

router = APIRouter(prefix="", tags=["AI"])


@router.post("/analyze/image", response_model=ImageAnalysis)
async def analyze_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    handler: AnalyzeImageHandler = Depends(get_analyze_image_handler),
):
    enforce_rate_limit(limiter_1_per_day, request)
    query = AnalyzeImageQuery(file=file)
    return await handler.handle(query)


@router.get("/expense_advisor", response_model=ExpenseAnalysis)
async def analyze(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    handler: GetExpenseAdvisorHandler = Depends(get_expense_advisor_handler),
):
    enforce_rate_limit(limiter_1_per_day, request)
    query = GetExpenseAdvisorQuery(user_id=cast(int, current_user.id))
    return await handler.handle(query)
