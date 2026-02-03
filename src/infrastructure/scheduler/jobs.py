import logging
import asyncio
from datetime import datetime

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

logger = logging.getLogger(__name__)


async def process_subscriptions_job_async():
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

            logger.info(f"Job finished at {datetime.now()} with stats: {stats}")

        except Exception as e:
            logger.error(f"Error processing subscriptions job: {e}")


def process_subscriptions_job():
    """Synchronous wrapper for the scheduler to call"""
    asyncio.run(process_subscriptions_job_async())
