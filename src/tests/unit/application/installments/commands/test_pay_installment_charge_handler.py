import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from application.installments.commands.pay_installment_charge import (
    PayInstallmentChargeCommand,
    PayInstallmentChargeHandler,
)
from domain.entities.account import Account
from domain.entities.installment_charge import InstallmentCharge
from domain.entities.installment_purchase import InstallmentPurchase
from domain.entities.transaction import Transaction
from domain.objects.enums import AccountType, InstallmentType, TransactionType
from domain.objects.money import Money
from shared.exceptions.domain import (
    InsufficientFundsError,
    InstallmentChargeAlreadyPaidError,
    SameAccountTransferError,
)


@pytest.mark.unit
class TestPayInstallmentChargeHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "account_repo": MagicMock(),
            "transaction_repo": MagicMock(),
            "charge_repo": MagicMock(),
            "purchase_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return PayInstallmentChargeHandler(
            account_repository=mocks["account_repo"],
            transaction_repository=mocks["transaction_repo"],
            installment_charge_repository=mocks["charge_repo"],
            installment_purchase_repository=mocks["purchase_repo"],
            uow=mocks["uow"],
        )

    @staticmethod
    def _purchase() -> InstallmentPurchase:
        return InstallmentPurchase(
            id=1,
            uuid="purchase-uuid",
            user_id=1,
            account_id=10,
            category_id=3,
            description="Laptop",
            total_amount=Money(Decimal("12000")),
            num_installments=12,
            installment_type=InstallmentType.NO_INTEREST,
            annual_interest_rate=Decimal("0"),
            monthly_payment=Decimal("1000"),
            purchase_date=date.today(),
            notes=None,
            is_active=True,
            creation_date=datetime.now(timezone.utc),
        )

    @staticmethod
    def _charge(*, paid=False) -> InstallmentCharge:
        return InstallmentCharge(
            id=1,
            uuid="charge-uuid",
            installment_purchase_id=1,
            installment_number=1,
            amount=Decimal("1000"),
            due_date=date.today(),
            paid=paid,
            creation_date=datetime.now(timezone.utc),
        )

    @staticmethod
    def _account(account_id, account_type, balance, name):
        return Account(
            id=account_id,
            uuid=f"account-{account_id}",
            user_id=1,
            bank_id=1,
            name=name,
            account_type=account_type,
            current_balance=Money(Decimal(balance)),
            is_active=True,
            creation_date=datetime.now(timezone.utc),
        )

    async def _setup_success(self, mocks):
        purchase = self._purchase()
        charge = self._charge()
        source = self._account(5, AccountType.CHECKING, "2000", "Nómina")
        card = self._account(10, AccountType.CREDIT_CARD, "38000", "TDC")
        incoming = Transaction(
            id=88,
            uuid="incoming-uuid",
            user_id=1,
            account_id=10,
            category_id=None,
            transaction_type=TransactionType.TRANSFER,
            amount=Money(Decimal("1000")),
            transaction_date=date.today(),
            creation_date=datetime.now(timezone.utc),
        )
        paid_charge = self._charge(paid=True)
        mocks["charge_repo"].get_by_uuid = AsyncMock(side_effect=[charge, charge])
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=source)
        mocks["account_repo"].get_by_id = AsyncMock(
            side_effect=lambda account_id, for_update: {5: source, 10: card}[account_id]
        )
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].create = AsyncMock(
            side_effect=[MagicMock(), incoming]
        )
        mocks["charge_repo"].update = AsyncMock(return_value=paid_charge)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(return_value=[paid_charge])
        mocks["purchase_repo"].update = AsyncMock()
        return source, card

    @pytest.mark.asyncio
    async def test_payment_creates_linked_transfer_and_updates_both_balances(
        self, handler, mocks
    ):
        source, card = await self._setup_success(mocks)

        result = await handler.handle(
            PayInstallmentChargeCommand(
                user_id=1,
                charge_uuid="charge-uuid",
                source_account_uuid="account-5",
                payment_date=date.today(),
            )
        )

        assert result.paid is True
        assert source.current_balance.amount == Decimal("1000")
        assert card.current_balance.amount == Decimal("39000")
        assert mocks["transaction_repo"].create.await_count == 2
        outgoing, incoming = [
            call.args[0] for call in mocks["transaction_repo"].create.await_args_list
        ]
        assert outgoing.transaction_type == TransactionType.TRANSFER
        assert incoming.transaction_type == TransactionType.TRANSFER
        assert outgoing.transfer_uuid == incoming.transfer_uuid
        assert outgoing.account_id == 5
        assert incoming.account_id == 10
        assert outgoing.category_id is None
        mocks["charge_repo"].update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_insufficient_source_funds(self, handler, mocks):
        charge = self._charge()
        source = self._account(5, AccountType.CHECKING, "999", "Nómina")
        card = self._account(10, AccountType.CREDIT_CARD, "38000", "TDC")
        mocks["charge_repo"].get_by_uuid = AsyncMock(return_value=charge)
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=self._purchase())
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=source)
        mocks["account_repo"].get_by_id = AsyncMock(
            side_effect=lambda account_id, for_update: {5: source, 10: card}[account_id]
        )

        with pytest.raises(InsufficientFundsError):
            await handler.handle(
                PayInstallmentChargeCommand(
                    user_id=1,
                    charge_uuid="charge-uuid",
                    source_account_uuid="account-5",
                    payment_date=date.today(),
                )
            )

        mocks["transaction_repo"].create.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_using_the_credit_card_as_source(self, handler, mocks):
        charge = self._charge()
        card = self._account(10, AccountType.CREDIT_CARD, "38000", "TDC")
        mocks["charge_repo"].get_by_uuid = AsyncMock(return_value=charge)
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=self._purchase())
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=card)

        with pytest.raises(SameAccountTransferError):
            await handler.handle(
                PayInstallmentChargeCommand(
                    user_id=1,
                    charge_uuid="charge-uuid",
                    source_account_uuid="account-10",
                    payment_date=date.today(),
                )
            )

    @pytest.mark.asyncio
    async def test_rejects_an_already_paid_charge(self, handler, mocks):
        charge = self._charge(paid=True)
        source = self._account(5, AccountType.CHECKING, "2000", "Nómina")
        card = self._account(10, AccountType.CREDIT_CARD, "38000", "TDC")
        mocks["charge_repo"].get_by_uuid = AsyncMock(side_effect=[charge, charge])
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=self._purchase())
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=source)
        mocks["account_repo"].get_by_id = AsyncMock(
            side_effect=lambda account_id, for_update: {5: source, 10: card}[account_id]
        )

        with pytest.raises(InstallmentChargeAlreadyPaidError):
            await handler.handle(
                PayInstallmentChargeCommand(
                    user_id=1,
                    charge_uuid="charge-uuid",
                    source_account_uuid="account-5",
                    payment_date=date.today(),
                )
            )
