import logging
from datetime import datetime, date, timedelta

from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.database.repositories.sqlalchemy_notification_repository import SQLAlchemyNotificationRepository
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
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from application.investments.commands.generate_daily_yields import (
    GenerateDailyYieldCommand,
    GenerateDailyYieldHandler,
)
from infrastructure.database.models.notifications import NotificationModel
from infrastructure.notifications.sse_manager import sse_manager
from sqlalchemy import select, delete, func


logger = logging.getLogger(__name__)


async def process_subscriptions_job():
    """Process due subscriptions - runs in the existing event loop"""
    logger.info(f"Processing subscriptions job at {datetime.now()}")

    async with AsyncSessionLocal() as db:
        try:
            sub_repo = SQLAlchemySubscriptionRepository(db)
            charge_repo = SQLAlchemySubscriptionChargeRepository(db)
            transaction_repo = SQLAlchemyTransactionRepository(db)
            notification_repo = SQLAlchemyNotificationRepository(db)

            processor = SubscriptionProcessor(
                subscription_repository=sub_repo,
                subscription_charge_repository=charge_repo,
                transaction_repository=transaction_repo,
                notification_repo=notification_repo
            )

            stats = await processor.process_due_subscriptions()
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
            transaction_repo = SQLAlchemyTransactionRepository(db)

            uow = SQLAlchemyUnitOfWork(db)
            handler = GenerateDailyYieldHandler(
                account_repository=account_repo,
                investment_yield_repository=yield_repo,
                transaction_repository=transaction_repo,
                uow=uow,
            )

            stats = await handler.handle(
                GenerateDailyYieldCommand(target_date=date.today())
            )

            logger.info(f"Job finished at {datetime.now()} with stats: {stats}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error processing investment yield job: {e}")

async def process_notification_job() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(NotificationModel).where(
                func.date(NotificationModel.created_at) <= date.today(),
                NotificationModel.is_read.is_(False),
            )
        )
        notifications = result.scalars().all()
        delivered_ids: set[int] = set()

        for notification in notifications:
            completed = await sse_manager.send_to_user(
                user_id=notification.user_id,
                data={
                    "title": notification.title,
                    "message": notification.message,
                    "type": notification.type.value,
                    "created_at": str(notification.created_at),
                }
            )

            if completed:
                delivered_ids.add(notification.id)

        if delivered_ids:
            await session.execute(
                delete(NotificationModel).where(
                    NotificationModel.id.in_(delivered_ids)
                )
            )
            await session.commit()
