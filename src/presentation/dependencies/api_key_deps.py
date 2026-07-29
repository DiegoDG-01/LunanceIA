from fastapi import Depends

from application.api_keys.commands.create_api_key import CreateAPIKeyHandler
from application.api_keys.commands.revoke_api_key import RevokeAPIKeyHandler
from application.api_keys.commands.delete_api_key import DeleteAPIKeyHandler
from application.api_keys.queries.list_api_keys import ListAPIKeysHandler
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.repositories.sqlalchemy_api_key_repository import (
    SQLAlchemyAPIKeyRepository,
)
from presentation.dependencies.repositories import (
    get_api_key_repository,
    get_unit_of_work_repository,
)


def get_create_api_key_handler(
    repo: SQLAlchemyAPIKeyRepository = Depends(get_api_key_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> CreateAPIKeyHandler:
    return CreateAPIKeyHandler(repo, uow)


def get_list_api_keys_handler(
    repo: SQLAlchemyAPIKeyRepository = Depends(get_api_key_repository),
) -> ListAPIKeysHandler:
    return ListAPIKeysHandler(repo)


def get_revoke_api_key_handler(
    repo: SQLAlchemyAPIKeyRepository = Depends(get_api_key_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> RevokeAPIKeyHandler:
    return RevokeAPIKeyHandler(repo, uow)


def get_delete_api_key_handler(
    repo: SQLAlchemyAPIKeyRepository = Depends(get_api_key_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> DeleteAPIKeyHandler:
    return DeleteAPIKeyHandler(repo, uow)
