import logging
from datetime import datetime, date

from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.database.repositories.sqlalchemy_subscription_repository import (
    SQLAlchemySubscriptionRepository,
)
from infrastructure.database.repositories.sqlalchemy_subscription_charge_repository import (
    SQLAlchemySubscriptionChargeRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)

from application.subscriptions.services.subscription_processor import (
    SubscriptionProcessor,
)
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_investment_yield_repository import (
    SQLAlchemyInvestmentYieldRepository,
)
from infrastructure.database.repositories.sqlalchemy_investment_card_repository import (
    SQLAlchemyInvestmentSettingsRepository,
)
from application.investments.commands.generate_daily_yields import (
    GenerateDailyYieldCommand,
    GenerateDailyYieldHandler,
)

logger = logging.getLogger(__name__)


async def process_subscriptions_job():
    """Process due subscriptions - runs in the existing event loop"""
    logger.info(f"Processing subscriptions job at {datetime.now()}")

    async with AsyncSessionLocal() as db:
        try:
            sub_repo = SQLAlchemySubscriptionRepository(db)
            charge_repo = SQLAlchemySubscriptionChargeRepository(db)
            transaction_repo = SQLAlchemyTransactionRepository(db)

            processor = SubscriptionProcessor(
                subscription_repository=sub_repo,
                subscription_charge_repository=charge_repo,
                transaction_repository=transaction_repo,
            )

            stats = await processor.process_due_subscriptions(db)
            await db.commit()

            logger.info(f"Job finished at {datetime.now()} with stats: {stats}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error processing subscriptions job: {e}")


async def process_investment_yield_job():
    logger.info(f"Processing investment yield job at {datetime.now()}")

    async with AsyncSessionLocal() as db:
        try:
            account_repo = SQLAlchemyAccountRepository(db)
            yield_repo = SQLAlchemyInvestmentYieldRepository(db)
            settings_repo = SQLAlchemyInvestmentSettingsRepository(db)

            handler = GenerateDailyYieldHandler(
                account_repository=account_repo,
                investment_yield_repository=yield_repo,
                investment_settings_repository=settings_repo,
            )

            stats = await handler.handle(
                GenerateDailyYieldCommand(target_date=date.today())
            )
            await db.commit()

            logger.info(f"Job finished at {datetime.now()} with stats: {stats}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error processing investment yield job: {e}")
