from fastapi import APIRouter

from presentation.api.v2.endpoints import account, auth, transaction

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(
    transaction.router, prefix="/transaction", tags=["transaction"]
)
