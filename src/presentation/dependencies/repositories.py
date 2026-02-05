from fastapi import Depends
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_bank_repository import (
    SQLAlchemyBankRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.database.repositories.sqlalchemy_auth_token_repository import (
    SQLAlchemyAuthTokenRepository,
)
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)
from infrastructure.database.repositories.sqlalchemy_dashboard_repository import (
    SQLAlchemyDashboardRepository,
)
from infrastructure.database.repositories.sqlalchemy_subscription_repository import (
    SQLAlchemySubscriptionRepository,
)
from infrastructure.database.repositories.sqlalchemy_subscription_charge_repository import (
    SQLAlchemySubscriptionChargeRepository,
)
from infrastructure.database.repositories.sqlalchemy_credit_card_repository import (
    SQLAlchemyCreditCardSettingsRepository,
)
from infrastructure.database.repositories.sqlalchemy_investment_card_repository import (
    SQLAlchemyInvestmentSettingsRepository,
)
from domain.repositories.auth_token_repository import AuthTokenRepository


def get_account_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyAccountRepository:
    return SQLAlchemyAccountRepository(db)


def get_user_repository(db: Session = Depends(get_db)) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(db)


def get_transaction_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyTransactionRepository:
    return SQLAlchemyTransactionRepository(db)


def get_category_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyCategoryRepository:
    return SQLAlchemyCategoryRepository(db)


def get_subscription_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemySubscriptionRepository:
    return SQLAlchemySubscriptionRepository(db)


def get_subscription_charge_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemySubscriptionChargeRepository:
    return SQLAlchemySubscriptionChargeRepository(db)


def get_credit_card_settings_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyCreditCardSettingsRepository:
    return SQLAlchemyCreditCardSettingsRepository(db)


def get_investment_settings_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyInvestmentSettingsRepository:
    return SQLAlchemyInvestmentSettingsRepository(db)


def get_auth_token_repository(db: Session = Depends(get_db)) -> AuthTokenRepository:
    return SQLAlchemyAuthTokenRepository(db)


def get_dashboard_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyDashboardRepository:
    return SQLAlchemyDashboardRepository(db)


def get_bank_repository(
    db: Session = Depends(get_db),
) -> SQLAlchemyBankRepository:
    return SQLAlchemyBankRepository(db)
