from fastapi import Depends

from domain.services.account_service import AccountService
from infrastructure.external_services.gemini import GeminiService
from infrastructure.security.jwt_service import JWTService
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from domain.repositories.auth_token_repository import AuthTokenRepository

from presentation.dependencies.repositories import (
    get_user_repository,
    get_auth_token_repository,
)


def get_account_service() -> AccountService:
    return AccountService()


def get_gemini_service() -> GeminiService:
    return GeminiService()


def get_jwt_service(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_token_repo: AuthTokenRepository = Depends(get_auth_token_repository),
) -> JWTService:
    return JWTService(user_repo, auth_token_repo)
