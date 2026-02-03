from datetime import date
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.subscription import Subscription
from domain.entities.transaction import Transaction
from domain.entities.subscription_charge import SubscriptionCharge
from domain.repositories.subscription_repository import SubscriptionRepository
from domain.repositories.subscription_charge_repository import (
    SubscriptionChargeRepository,
)
from domain.repositories.transaction_repository import TransactionRepository
from domain.objects.enums import TransactionType

logger = logging.getLogger(__name__)


class SubscriptionProcessor:
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        subscription_charge_repository: SubscriptionChargeRepository,
        transaction_repository: TransactionRepository,
    ):
        self.subscription_repository = subscription_repository
        self.subscription_charge_repository = subscription_charge_repository
        self.transaction_repository = transaction_repository

    async def process_due_subscriptions(self, db: AsyncSession) -> dict:
        logger.info("Processing due subscriptions")

        stats = {
            "processed": 0,
            "created": 0,
            "skipped": 0,
            "failed": 0,
        }

        try:
            active_subscriptions = (
                await self.subscription_repository.get_active_subscriptions()
            )

            for subscription in active_subscriptions:
                stats["processed"] += 1

                try:
                    if await self._should_generate_transaction(subscription, db):
                        await self._create_transaction_from_subscription(
                            subscription, db
                        )
                        stats["created"] += 1
                        logger.debug(
                            f"Transaction created for subscription {subscription.uuid}"
                        )
                    else:
                        stats["skipped"] += 1
                        logger.debug(
                            f"Transaction skipped for subscription {subscription.uuid}"
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing due subscription {subscription.uuid}: {e}"
                    )
                    stats["failed"] += 1

            await db.commit()
            logger.info(f"Processed {stats['processed']} subscriptions")

        except Exception as e:
            logger.error(f"Error processing due subscriptions: {e}")
            stats["failed"] = 1
            raise

        return stats

    async def _should_generate_transaction(
        self, subscription: Subscription, db: AsyncSession
    ) -> bool:
        today = date.today()

        if subscription.end_date and subscription.end_date < today:
            return False

        if subscription.billing_day != today.day:
            return False

        existing_charge = (
            await self.subscription_charge_repository.get_by_subscription_and_month(
                subscription_id=subscription.id,
                year=today.year,
                month=today.month,
            )
        )

        if existing_charge:
            logger.debug(
                f"Charge already exists for subscription {subscription.uuid} in {today.year}-{today.month}"
            )
            return False
        return True

    async def _create_transaction_from_subscription(
        self, subscription: Subscription, db: AsyncSession
    ) -> Transaction:
        today = date.today()

        charge = SubscriptionCharge.create_pending(
            subscription_id=subscription.id,
            charge_date=today,
            amount=subscription.amount,
        )

        save_charge = await self.subscription_charge_repository.create(charge)

        transaction = Transaction.create_new(
            user_id=subscription.user_id,
            account_id=subscription.account_id,
            category_id=subscription.category_id,
            amount=subscription.amount,
            transaction_type=TransactionType.EXPENSE,
            description=f"Subscription: {subscription.name}",
            transaction_date=today,
        )

        created_transaction = await self.transaction_repository.create(transaction)

        save_charge.mark_as_paid(created_transaction.id)
        await self.subscription_charge_repository.update(save_charge)

        return created_transaction
