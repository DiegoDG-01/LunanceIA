###
###    MOVE CODE TO AI FILE
###


# from slowapi import Limiter
# from fastapi import APIRouter, Depends, Request
#
# from domain.entities.expense_suggestion import ExpenseAnalysis
# from domain.entities.user import User
# from slowapi.util import get_remote_address
#
# from presentation.dependencies import get_current_active_user
# from presentation.dependencies import get_expense_advisor_handler
# from application.expense.expense_advisor import (
#     GetExpenseAdvisorHandler,
#     GetExpenseAdvisorQuery,
# )
#
# router = APIRouter(prefix="", tags=["Expense Advisor"])
# limiter = Limiter(key_func=get_remote_address)
#
#
# @router.get("/analyze", response_model=ExpenseAnalysis)
# @limiter.limit("1/day")
# async def analyze(
#     request: Request,
#     current_user: User = Depends(get_current_active_user),
#     handler: GetExpenseAdvisorHandler = Depends(get_expense_advisor_handler),
# ):
#     query = GetExpenseAdvisorQuery(user_id=current_user.id)
#     return await handler.handle(query)
