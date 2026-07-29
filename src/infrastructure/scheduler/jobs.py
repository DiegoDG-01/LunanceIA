import logging
from datetime import datetime, date, timezone

from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.database.repositories.sqlalchemy_notification_repository import (
    SQLAlchemyNotificationRepository,
)
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
from application.incomes.services.income_processor import IncomeProcessor
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_investment_yield_repository import (
    SQLAlchemyInvestmentYieldRepository,
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from application.investments.commands.generate_daily_yields import (
    GenerateDailyYieldCommand,
    GenerateDailyYieldHandler,
)

from infrastructure.database.repositories.sqlalchemy_income_deposit_repository import (
    SQLAlchemyIncomeDepositRepository,
)
from infrastructure.database.repositories.sqlalchemy_recurring_income_repository import (
    SQLAlchemyRecurringIncomeRepository,
)


logger = logging.getLogger(__name__)


async def process_subscriptions_job():
    """Process due subscriptions - runs in the existing event loop"""
    logger.info(f"Processing subscriptions job at {datetime.now(timezone.utc)}")

    async with AsyncSessionLocal() as db:
        try:
            sub_repo = SQLAlchemySubscriptionRepository(db)
            charge_repo = SQLAlchemySubscriptionChargeRepository(db)
            transaction_repo = SQLAlchemyTransactionRepository(db)
            notification_repo = SQLAlchemyNotificationRepository(db)
            account_repo = SQLAlchemyAccountRepository(db)

            processor = SubscriptionProcessor(
                subscription_repository=sub_repo,
                subscription_charge_repository=charge_repo,
                transaction_repository=transaction_repo,
                notification_repo=notification_repo,
                account_repository=account_repo,
            )

            stats = await processor.process_due_subscriptions()
            await db.commit()

            logger.info(
                f"Job finished at {datetime.now(timezone.utc)} with stats: {stats}"
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Error processing subscriptions job: {e}")


async def process_investment_yield_job():
    logger.info(f"Processing investment yield job at {datetime.now(timezone.utc)}")

    async with AsyncSessionLocal() as db:
        try:
            account_repo = SQLAlchemyAccountRepository(db)
            yield_repo = SQLAlchemyInvestmentYieldRepository(db)
            transaction_repo = SQLAlchemyTransactionRepository(db)
            notification_repo = SQLAlchemyNotificationRepository(db)

            uow = SQLAlchemyUnitOfWork(db)
            handler = GenerateDailyYieldHandler(
                account_repository=account_repo,
                investment_yield_repository=yield_repo,
                transaction_repository=transaction_repo,
                notification_repository=notification_repo,
                uow=uow,
            )

            stats = await handler.handle(
                GenerateDailyYieldCommand(target_date=date.today())
            )

            logger.info(
                f"Job finished at {datetime.now(timezone.utc)} with stats: {stats}"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Error processing investment yield job: {e}")


async def process_recurring_income_job():
    """Process due incomes - runs in the existing event loop"""
    logger.info(f"Processing recurring income job at {datetime.now(timezone.utc)}")

    async with AsyncSessionLocal() as db:
        try:
            recurring_income_repo = SQLAlchemyRecurringIncomeRepository(db)
            deposit_repo = SQLAlchemyIncomeDepositRepository(db)
            transaction_repo = SQLAlchemyTransactionRepository(db)
            account_repo = SQLAlchemyAccountRepository(db)
            notification_repo = SQLAlchemyNotificationRepository(db)

            processor = IncomeProcessor(
                recurring_income_repository=recurring_income_repo,
                income_deposit_repository=deposit_repo,
                transaction_repository=transaction_repo,
                account_repository=account_repo,
                notification_repository=notification_repo,
            )

            stats = await processor.process_due_incomes()
            await db.commit()

            logger.info(
                f"Job finished at {datetime.now(timezone.utc)} with stats: {stats}"
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Error processing recurring income job: {e}")
