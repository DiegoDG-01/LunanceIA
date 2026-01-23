from fastapi import APIRouter

from presentation.api.v2.endpoints import account, auth, transaction, category, dashboard, subscription

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(category.router, prefix="/category", tags=["category"])
api_router.include_router(transaction.router, prefix="/transaction", tags=["transaction"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(subscription.router, prefix="/subscription", tags=["subscription"])
