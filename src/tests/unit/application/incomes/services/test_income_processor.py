"""Unit tests for IncomeProcessor."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.incomes.services.income_processor import IncomeProcessor
from domain.entities.account import Account
from domain.entities.recurring_income import RecurringIncome
from domain.entities.transaction import Transaction
from domain.objects.enums import AccountType, Frequency, TransactionType
from domain.objects.money import Money
from shared.exceptions.domain import AccountNotFoundError

TODAY = date(2026, 7, 17)


def make_income(**overrides) -> RecurringIncome:
    defaults = {
        "user_id": 10,
        "account_id": 20,
        "category_id": 5,
        "name": "Nómina",
        "amount": Money(Decimal("5000.00")),
        "frequency": Frequency.BIWEEKLY,
        "start_date": date(2026, 7, 1),
    }
    defaults.update(overrides)
    income = RecurringIncome.create_new(**defaults)
    income.id = 1
    income.uuid = "income-123"
    return income


def make_account(balance: str = "1000.00") -> Account:
    account = Account.create_new(
        user_id=10,
        bank_id=1,
        name="Cuenta Test",
        account_type=AccountType.CHECKING,
        initial_balance=Money(Decimal(balance)),
    )
    account.id = 20
    return account


@pytest.mark.unit
class TestIncomeProcessor:
    @pytest.fixture
    def mocks(self):
        income_repo = MagicMock()
        income_repo.get_due_incomes = AsyncMock(return_value=[])
        income_repo.update = AsyncMock()

        deposit_repo = MagicMock()
        deposit_repo.get_by_income_and_date = AsyncMock(return_value=None)
        deposit_repo.create = AsyncMock(side_effect=lambda deposit: deposit)
        deposit_repo.update = AsyncMock(side_effect=lambda deposit: deposit)

        tx_repo = MagicMock()
        mock_tx = MagicMock(spec=Transaction)
        mock_tx.id = 100
        tx_repo.create = AsyncMock(return_value=mock_tx)

        account_repo = MagicMock()
        account_repo.get_by_id = AsyncMock(return_value=make_account())
        account_repo.update = AsyncMock()

        notification_repo = MagicMock()
        notification_repo.create = AsyncMock()

        return {
            "income_repo": income_repo,
            "deposit_repo": deposit_repo,
            "tx_repo": tx_repo,
            "account_repo": account_repo,
            "notification_repo": notification_repo,
        }

    @pytest.fixture
    def processor(self, mocks):
        return IncomeProcessor(
            recurring_income_repository=mocks["income_repo"],
            income_deposit_repository=mocks["deposit_repo"],
            transaction_repository=mocks["tx_repo"],
            account_repository=mocks["account_repo"],
            notification_repository=mocks["notification_repo"],
        )

    async def test_no_due_incomes_does_nothing(self, processor, mocks):
        stats = await processor.process_due_incomes()

        assert stats == {"processed": 0, "created": 0, "failed": 0}
        mocks["deposit_repo"].create.assert_not_called()

    async def test_single_due_income_deposits_and_updates_balance(
        self, processor, mocks
    ):
        income = make_income(
            frequency=Frequency.MONTHLY,
            start_date=TODAY,
        )
        account = make_account("1000.00")
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)

        created = await processor._process_income(income, TODAY)

        assert created == 1
        assert account.current_balance.amount == Decimal("6000.00")
        mocks["account_repo"].get_by_id.assert_awaited_once_with(
            income.account_id, for_update=True
        )
        mocks["account_repo"].update.assert_called_once_with(account)
        mocks["income_repo"].update.assert_called_once_with(income)
        assert income.next_payment_date > TODAY

    async def test_catch_up_generates_one_deposit_per_missed_period(
        self, processor, mocks
    ):
        # Quincenal vencida desde el 1-jul: debe recuperar 1-jul y 15-jul
        income = make_income(
            frequency=Frequency.BIWEEKLY,
            start_date=date(2026, 7, 1),
        )
        account = make_account("0.00")
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)

        created = await processor._process_income(income, TODAY)

        assert created == 2
        assert account.current_balance.amount == Decimal("10000.00")
        assert income.next_payment_date == date(2026, 7, 29)

        # Cada transacción lleva la fecha del periodo, no la de hoy
        tx_dates = [
            call.args[0].transaction_date
            for call in mocks["tx_repo"].create.call_args_list
        ]
        assert tx_dates == [date(2026, 7, 1), date(2026, 7, 15)]

    async def test_transactions_are_income_type(self, processor, mocks):
        income = make_income(frequency=Frequency.MONTHLY, start_date=TODAY)

        await processor._process_income(income, TODAY)

        transaction = mocks["tx_repo"].create.call_args.args[0]
        assert transaction.transaction_type == TransactionType.INCOME
        assert transaction.amount.amount == Decimal("5000.00")

    async def test_existing_deposit_is_skipped_but_date_advances(
        self, processor, mocks
    ):
        # El periodo ya fue depositado (job corrió dos veces): no duplica dinero,
        # pero la fecha avanza para auto-repararse.
        income = make_income(frequency=Frequency.MONTHLY, start_date=TODAY)
        mocks["deposit_repo"].get_by_income_and_date = AsyncMock(
            return_value=MagicMock()
        )

        created = await processor._process_income(income, TODAY)

        assert created == 0
        mocks["deposit_repo"].create.assert_not_called()
        mocks["tx_repo"].create.assert_not_called()
        mocks["notification_repo"].create.assert_not_called()
        assert income.next_payment_date > TODAY
        mocks["income_repo"].update.assert_called_once_with(income)

    async def test_deposit_marked_paid_with_transaction_id(self, processor, mocks):
        income = make_income(frequency=Frequency.MONTHLY, start_date=TODAY)

        await processor._process_income(income, TODAY)

        updated_deposit = mocks["deposit_repo"].update.call_args.args[0]
        assert updated_deposit.transaction_id == 100
        assert updated_deposit.deposit_date == TODAY

    async def test_notification_sent_once_even_with_catch_up(self, processor, mocks):
        income = make_income(frequency=Frequency.BIWEEKLY, start_date=date(2026, 7, 1))

        created = await processor._process_income(income, TODAY)

        assert created == 2
        mocks["notification_repo"].create.assert_called_once()

    async def test_account_not_found_writes_nothing(self, processor, mocks):
        income = make_income(frequency=Frequency.MONTHLY, start_date=TODAY)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(AccountNotFoundError):
            await processor._process_income(income, TODAY)

        mocks["deposit_repo"].create.assert_not_called()
        mocks["tx_repo"].create.assert_not_called()

    async def test_failing_income_does_not_stop_others(self, processor, mocks):
        # El primero apunta a cuenta inexistente; el segundo debe procesarse igual.
        broken = make_income(frequency=Frequency.MONTHLY, start_date=TODAY)
        broken.uuid = "broken-1"
        healthy = make_income(frequency=Frequency.MONTHLY, start_date=TODAY)
        healthy.id = 2
        healthy.uuid = "healthy-2"

        mocks["income_repo"].get_due_incomes = AsyncMock(return_value=[broken, healthy])
        account = make_account()
        mocks["account_repo"].get_by_id = AsyncMock(
            side_effect=lambda account_id, *, for_update=False: (
                None if account_id == 20 else account
            )
        )
        broken.account_id = 20
        healthy.account_id = 21

        stats = await processor.process_due_incomes()

        assert stats["processed"] == 2
        assert stats["failed"] == 1
        assert stats["created"] >= 1

    async def test_inactive_income_not_processed(self, processor, mocks):
        # Vencido pero pausado: is_due lo frena aunque la query lo devolviera.
        income = make_income(frequency=Frequency.MONTHLY, start_date=date(2026, 7, 1))
        income.deactivate()

        created = await processor._process_income(income, TODAY)

        assert created == 0
        mocks["deposit_repo"].create.assert_not_called()

    async def test_expired_income_stops_at_end_date(self, processor, mocks):
        # Quincenal que terminó el 10-jul: solo recupera el periodo del 1-jul.
        income = make_income(
            frequency=Frequency.BIWEEKLY,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
        )

        created = await processor._process_income(income, TODAY)

        assert created == 1
        transaction = mocks["tx_repo"].create.call_args.args[0]
        assert transaction.transaction_date == date(2026, 7, 1)
