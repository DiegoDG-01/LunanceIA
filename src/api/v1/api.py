from fastapi import APIRouter

from .endpoints import transacciones, auth, user

api_router = APIRouter()

api_router.include_router(transacciones.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/users", tags=["users"])