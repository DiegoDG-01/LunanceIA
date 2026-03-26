from fastapi import APIRouter, Depends, Request, UploadFile, File
from slowapi import Limiter
from slowapi.util import get_remote_address

from domain.entities.image_analysis import ImageAnalysis
from domain.entities.user import User
from domain.entities.expense_suggestion import ExpenseAnalysis

from presentation.dependencies.ai_deps import get_analyze_image_handler
from application.ai.queries.analyze_image import AnalyzeImageQuery, AnalyzeImageHandler
from presentation.dependencies import get_current_active_user
from presentation.dependencies import get_expense_advisor_handler
from application.ai.queries.expense_advisor import (
    GetExpenseAdvisorHandler,
    GetExpenseAdvisorQuery,
)

router = APIRouter(prefix="", tags=["AI"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/analyze/image", response_model=ImageAnalysis)
@limiter.limit("2/day")
async def analyze_image(
    request: Request,
    file: UploadFile = File(...),
    # current_user: User = Depends(get_current_active_user),
    handler: AnalyzeImageHandler = Depends(get_analyze_image_handler),
):
    image_data = await file.read()
    query = AnalyzeImageQuery(image_data=image_data, mime_type=file.content_type)
    return await handler.handle(query)


@router.get("/expense_advisor", response_model=ExpenseAnalysis)
@limiter.limit("1/day")
async def analyze(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    handler: GetExpenseAdvisorHandler = Depends(get_expense_advisor_handler),
):
    query = GetExpenseAdvisorQuery(user_id=current_user.id)
    return await handler.handle(query)
