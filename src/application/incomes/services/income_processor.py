from typing import cast
from datetime import date, timezone, datetime

import logging
from domain.entities.recurring_income import RecurringIncome
from domain.repositories.account_repository import AccountRepository
from domain.repositories.income_deposit_repository import IncomeDepositRepository
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.recurring_income_repository import RecurringIncomeRepository
from domain.repositories.transaction_repository import TransactionRepository
from shared.exceptions.domain import AccountNotFoundError
from domain.entities.income_deposit import IncomeDeposit
from domain.entities.transaction import Transaction
from domain.objects.enums import NotificationType, TransactionType
from domain.entities.notification import Notification


logger = logging.getLogger(__name__)


class IncomeProcessor:
    def __init__(
        self,
        recurring_income_repository: RecurringIncomeRepository,
        income_deposit_repository: IncomeDepositRepository,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        notification_repository: NotificationRepository,
    ):
        self.recurring_income_repository = recurring_income_repository
        self.income_deposit_repository = income_deposit_repository
        self.transaction_repository = transaction_repository
        self.account_repository = account_repository
        self.notification_repository = notification_repository

    async def process_due_incomes(self) -> dict:
        logger.info("Processing due incomes")

        today = datetime.now(timezone.utc).date()

        stats = {
            "processed": 0,
            "created": 0,
            "failed": 0,
        }

        try:
            due_incomes = await self.recurring_income_repository.get_due_incomes(today)

            for income in due_incomes:
                stats["processed"] += 1
                try:
                    created = await self._process_income(income, today)
                    stats["created"] += created
                except Exception as e:
                    logger.error(
                        f"Error processing income {income.id}: {e}", exc_info=True
                    )
                    stats["failed"] += 1

            logger.info(f"Processed {stats['processed']} incomes")
        except Exception as e:
            logger.error(f"Error processing due incomes: {e}", exc_info=True)
            raise

        return stats

    async def _process_income(self, income: RecurringIncome, today: date) -> int:
        created = 0

        while income.is_due(today):
            deposit_made = await self._create_deposit(income, income.next_payment_date)
            if deposit_made:
                created += 1
            income.advance_next_payment()

        await self.recurring_income_repository.update(income)

        if created > 0:
            notification = Notification.create_new(
                user_id=income.user_id,
                title="Income created",
                message=f"Income created for {income.name}",
                type=NotificationType.PUSH,
                is_read=False,
            )
            await self.notification_repository.create(notification)

        return created

    async def _create_deposit(
        self, income: RecurringIncome, payment_date: date
    ) -> bool:
        existing = await self.income_deposit_repository.get_by_income_and_date(
            recurring_income_id=cast(int, income.id), deposit_date=payment_date
        )
        if existing:
            logger.info(f"Deposit already exists for {income.name} on {payment_date}")
            return False

        account = await self.account_repository.get_by_id(income.account_id)
        if not account:
            raise AccountNotFoundError(str(income.account_id))

        new_balance = account.current_balance.add(income.amount)
        account.update_balance(new_balance)

        deposit = IncomeDeposit.create_pending(
            recurring_income_id=cast(int, income.id),
            deposit_date=payment_date,
            amount=income.amount,
        )
        saved_deposit = await self.income_deposit_repository.create(deposit)

        transaction = Transaction.create_new(
            user_id=income.user_id,
            account_id=income.account_id,
            category_id=income.category_id,
            transaction_type=TransactionType.INCOME,
            amount=income.amount,
            transaction_date=payment_date,
            description=f"Ingreso recurrente: {income.name}",
        )
        created_transaction = await self.transaction_repository.create(transaction)

        await self.account_repository.update(account)

        saved_deposit.mark_as_paid(cast(int, created_transaction.id))
        await self.income_deposit_repository.update(saved_deposit)

        return True
