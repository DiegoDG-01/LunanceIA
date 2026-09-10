from fastapi import Depends

from application.interfaces.auth_service import AuthTokenServiceInterface
from domain.repositories.auth_token_repository import AuthTokenRepository
from domain.services.account_service import AccountService
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.security.jwt_service import JWTService
from presentation.dependencies.repositories import (
    get_auth_token_repository,
    get_user_repository,
)


def get_account_service() -> AccountService:
    return AccountService()


def get_jwt_service(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_token_repo: AuthTokenRepository = Depends(get_auth_token_repository),
) -> AuthTokenServiceInterface:
    return JWTService(user_repo, auth_token_repo)
