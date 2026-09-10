import logging
from datetime import date
from typing import cast

from domain.entities.notification import Notification
from domain.entities.subscription import Subscription
from domain.entities.subscription_charge import SubscriptionCharge
from domain.entities.transaction import Transaction
from domain.objects.enums import NotificationType, TransactionType
from domain.repositories.account_repository import AccountRepository
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.subscription_charge_repository import (
    SubscriptionChargeRepository,
)
from domain.repositories.subscription_repository import SubscriptionRepository
from domain.repositories.transaction_repository import TransactionRepository
from shared.exceptions.domain import AccountNotFoundError

logger = logging.getLogger(__name__)

MAX_CATCHUP_PERIODS = 60


class SubscriptionProcessor:
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        subscription_charge_repository: SubscriptionChargeRepository,
        transaction_repository: TransactionRepository,
        notification_repo: NotificationRepository,
        account_repository: AccountRepository,
    ):
        self.subscription_repository = subscription_repository
        self.subscription_charge_repository = subscription_charge_repository
        self.transaction_repository = transaction_repository
        self.notification_repo = notification_repo
        self.account_repository = account_repository

    async def process_due_subscriptions(self) -> dict:
        logger.info("Processing due subscriptions")
        today = date.today()

        stats = {
            "processed": 0,
            "created": 0,
            "skipped": 0,
            "failed": 0,
        }

        try:
            due_subscriptions = (
                await self.subscription_repository.get_due_subscriptions(today)
            )

            for subscription in due_subscriptions:
                stats["processed"] += 1

                try:
                    created = await self._process_subscription(subscription, today)
                    stats["created"] += created
                    if created == 0:
                        stats["skipped"] += 1
                except Exception as e:
                    logger.error(
                        f"Error processing due subscription {subscription.uuid}: {e}",
                        exc_info=True,
                    )
                    stats["failed"] += 1

            logger.info(f"Processed {stats['processed']} subscriptions")
        except Exception as e:
            logger.error(f"Error processing due subscriptions: {e}", exc_info=True)
            stats["failed"] = 1
            raise

        return stats

    async def _process_subscription(
        self, subscription: Subscription, today: date
    ) -> int:
        created = 0
        guard = 0

        while subscription.is_due(today) and guard < MAX_CATCHUP_PERIODS:
            charged = await self._create_charge(
                subscription, subscription.next_charge_date
            )
            if charged:
                created += 1
            subscription.advance_next_charge()
            guard += 1

        await self.subscription_repository.update(subscription)

        if created > 0:
            notification = Notification.create_new(
                user_id=subscription.user_id,
                title=f"Subscription: {subscription.name}",
                message="Your subscription payment has been processed.",
                type=NotificationType.PUSH,
                is_read=False,
            )
            await self.notification_repo.create(notification)

        return created

    async def _create_charge(
        self, subscription: Subscription, charge_date: date
    ) -> bool:
        # TODO(multi-instancia): al escalar a >1 worker/réplica, hacer este
        # cargo atómico por unidad (UoW + commit por cargo), re-verificar la
        # idempotencia después de bloquear la cuenta y capturar el
        # IntegrityError de uq_subscription_charge_date como backstop.
        existing = (
            await self.subscription_charge_repository.get_by_subscription_and_date(
                subscription_id=cast(int, subscription.id),
                charge_date=charge_date,
            )
        )
        if existing:
            logger.info(
                f"Charge already exists for subscription {subscription.uuid} on {charge_date}"
            )
            return False

        account = await self.account_repository.get_by_id(
            subscription.account_id, for_update=True
        )
        if account is None:
            raise AccountNotFoundError(str(subscription.account_id))

        new_balance = account.current_balance.subtract(subscription.amount)
        account.update_balance(new_balance)

        charge = SubscriptionCharge.create_pending(
            subscription_id=cast(int, subscription.id),
            charge_date=charge_date,
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
            transaction_date=charge_date,
        )
        created_transaction = await self.transaction_repository.create(transaction)

        await self.account_repository.update(account)

        save_charge.mark_as_paid(cast(int, created_transaction.id))
        await self.subscription_charge_repository.update(save_charge)

        return True
