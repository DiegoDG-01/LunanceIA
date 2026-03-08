from fastapi import Depends

from application.auth.commands.login import LoginHandler
from application.auth.commands.register import RegisterHandler
from application.auth.commands.refresh_token import RefreshTokenHandler
from application.auth.commands.logout import LogoutHandler
from domain.repositories.auth_token_repository import AuthTokenRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.security.jwt_service import JWTService

from presentation.dependencies.repositories import (
    get_user_repository,
    get_auth_token_repository,
    get_unit_of_work_repository,
)
from presentation.dependencies.services import get_jwt_service


def get_login_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_token_repo: AuthTokenRepository = Depends(get_auth_token_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> LoginHandler:
    return LoginHandler(user_repo, auth_token_repo, jwt_service, uow)


def get_register_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> RegisterHandler:
    return RegisterHandler(user_repo, jwt_service, uow)


def get_refresh_token_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_token_repository: AuthTokenRepository = Depends(get_auth_token_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> RefreshTokenHandler:
    return RefreshTokenHandler(user_repo, auth_token_repository, jwt_service)


def get_logout_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    auth_token_repository: AuthTokenRepository = Depends(get_auth_token_repository),
    jwt_service: JWTService = Depends(get_jwt_service),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> LogoutHandler:
    return LogoutHandler(user_repo, auth_token_repository, jwt_service, uow)
