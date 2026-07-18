from fastapi import APIRouter

from presentation.api.v2.endpoints import (
    account,
    auth,
    transaction,
    category,
    dashboard,
    subscription,
    bank,
    investment_yield,
    ai,
    notification,
    installment,
    budget,
    goals,
    transfer,
    api_key,
    income,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(category.router, prefix="/category", tags=["category"])
api_router.include_router(
    transaction.router, prefix="/transaction", tags=["transaction"]
)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(
    subscription.router, prefix="/subscription", tags=["subscription"]
)
api_router.include_router(bank.router, prefix="/bank", tags=["bank"])
api_router.include_router(
    investment_yield.router, prefix="/investments", tags=["Investment Yield"]
)
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(
    notification.router, prefix="/notifications", tags=["Notifications"]
)
api_router.include_router(
    installment.router, prefix="/installments", tags=["Installments"]
)
api_router.include_router(budget.router, prefix="/budgets", tags=["Budgets"])
api_router.include_router(goals.router, prefix="/goals", tags=["Goals"])
api_router.include_router(transfer.router, prefix="/transfers", tags=["Transfer"])
api_router.include_router(api_key.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(income.router, prefix="/incomes", tags=["Incomes"])
