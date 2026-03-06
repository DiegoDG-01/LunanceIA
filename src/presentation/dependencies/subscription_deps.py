from fastapi import Depends

from application.subscriptions.commands.create_subscription import (
    CreateSubscriptionHandler,
)
from application.subscriptions.commands.update_subscription import (
    UpdateSubscriptionHandler,
)
from application.subscriptions.commands.delete_subscription import (
    DeleteSubscriptionHandler,
)
from application.subscriptions.commands.state_subscription import (
    StateSubscriptionHandler,
)
from application.subscriptions.queries.get_subscriptions import GetSubscriptionsHandler
from application.subscriptions.queries.get_subscriptions_by_id import (
    GetSubscriptionsByIdHandler,
)
from application.subscriptions.queries.get_subscription_charges import (
    GetSubscriptionChargesHandler,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)
from infrastructure.database.repositories.sqlalchemy_subscription_repository import (
    SQLAlchemySubscriptionRepository,
)
from infrastructure.database.repositories.sqlalchemy_subscription_charge_repository import (
    SQLAlchemySubscriptionChargeRepository,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)

from presentation.dependencies.repositories import (
    get_account_repository,
    get_user_repository,
    get_category_repository,
    get_subscription_repository,
    get_subscription_charge_repository,
    get_unit_of_work_repository,
)


def get_create_subscription_handler(
    subscription_repo: SQLAlchemySubscriptionRepository = Depends(
        get_subscription_repository
    ),
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> CreateSubscriptionHandler:
    return CreateSubscriptionHandler(
        subscription_repo, user_repo, account_repo, category_repo, uow
    )


def get_update_subscription_handler(
    subscription_respo: SQLAlchemySubscriptionRepository = Depends(
        get_subscription_repository
    ),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> UpdateSubscriptionHandler:
    return UpdateSubscriptionHandler(
        subscription_respo, category_repo, account_repo, uow
    )


def get_state_subscription_handler(
    subscription_repo: SQLAlchemySubscriptionRepository = Depends(
        get_subscription_repository
    ),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> StateSubscriptionHandler:
    return StateSubscriptionHandler(subscription_repo, category_repo, account_repo, uow)


def get_subscriptions_handler(
    subscription_repo: SQLAlchemySubscriptionRepository = Depends(
        get_subscription_repository
    ),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> GetSubscriptionsHandler:
    return GetSubscriptionsHandler(subscription_repo, account_repo, category_repo)


def get_subscription_by_id_handler(
    subscription_repo: SQLAlchemySubscriptionRepository = Depends(
        get_subscription_repository
    ),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> GetSubscriptionsByIdHandler:
    return GetSubscriptionsByIdHandler(subscription_repo, account_repo, category_repo)


def get_subscription_charges_handler(
    subscription_charge_repo: SQLAlchemySubscriptionChargeRepository = Depends(
        get_subscription_charge_repository
    ),
) -> GetSubscriptionChargesHandler:
    return GetSubscriptionChargesHandler(subscription_charge_repo)


def get_delete_subscription_handler(
    subscription_repo: SQLAlchemySubscriptionRepository = Depends(
        get_subscription_repository
    ),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> DeleteSubscriptionHandler:
    return DeleteSubscriptionHandler(subscription_repo, uow)
