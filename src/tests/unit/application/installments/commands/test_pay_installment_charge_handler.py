import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime

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
from shared.exceptions.domain import AccountNotFoundError, InstallmentChargeNotFoundError


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

    def _make_account(self, balance: Decimal = Decimal("38000.00")) -> Account:
        return Account(
            id=10, uuid="acc-uuid-1", user_id=1, bank_id=1,
            name="BBVA TDC", account_type=AccountType.CREDIT_CARD,
            current_balance=Money(balance),
            is_active=True, creation_date=datetime.now(),
        )

    def _make_purchase(self, num_installments: int = 12) -> InstallmentPurchase:
        return InstallmentPurchase(
            id=1, uuid="purchase-uuid-1", user_id=1, account_id=10,
            category_id=None, description="iPhone 15 Pro",
            total_amount=Money(Decimal("12000.00")),
            num_installments=num_installments,
            installment_type=InstallmentType.NO_INTEREST,
            annual_interest_rate=Decimal("0"),
            monthly_payment=Decimal("1000.00"),
            purchase_date=date.today(), notes=None,
            is_active=True, creation_date=datetime.now(),
        )

    def _make_charge(self, installment_number: int = 1, paid: bool = False) -> InstallmentCharge:
        return InstallmentCharge(
            id=installment_number, uuid=f"charge-uuid-{installment_number}",
            installment_purchase_id=1, installment_number=installment_number,
            amount=Decimal("1000.00"), due_date=date.today(),
            paid=paid, creation_date=datetime.now(),
        )

    def _make_transaction(self) -> Transaction:
        return Transaction(
            id=99, uuid="tx-uuid-1", user_id=1, account_id=10,
            category_id=None, transaction_type=TransactionType.INCOME,
            amount=Money(Decimal("1000.00")), transaction_date=date.today(),
            creation_date=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_pay_charge_success(self, handler, mocks):
        charge = self._make_charge(installment_number=1)
        purchase = self._make_purchase()
        account = self._make_account()
        transaction = self._make_transaction()
        paid_charge = self._make_charge(installment_number=1, paid=True)

        mocks["charge_repo"].get_by_uuid = AsyncMock(return_value=charge)
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].create = AsyncMock(return_value=transaction)
        mocks["charge_repo"].update = AsyncMock(return_value=paid_charge)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(return_value=[paid_charge])
        mocks["purchase_repo"].update = AsyncMock()

        result = await handler.handle(PayInstallmentChargeCommand(
            user_id=1, charge_uuid="charge-uuid-1", payment_date=date.today()
        ))

        assert result.paid is True
        mocks["transaction_repo"].create.assert_called_once()
        mocks["account_repo"].update.assert_called_once()

    @pytest.mark.asyncio
    async def test_balance_increases_on_payment(self, handler, mocks):
        charge = self._make_charge()
        purchase = self._make_purchase()
        account = self._make_account(balance=Decimal("38000.00"))
        transaction = self._make_transaction()
        paid_charge = self._make_charge(paid=True)

        mocks["charge_repo"].get_by_uuid = AsyncMock(return_value=charge)
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].create = AsyncMock(return_value=transaction)
        mocks["charge_repo"].update = AsyncMock(return_value=paid_charge)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(return_value=[paid_charge])
        mocks["purchase_repo"].update = AsyncMock()

        await handler.handle(PayInstallmentChargeCommand(
            user_id=1, charge_uuid="charge-uuid-1", payment_date=date.today()
        ))

        # 38000 + 1000 = 39000 (crédito disponible aumenta al pagar)
        assert account.current_balance.amount == Decimal("39000.00")

    @pytest.mark.asyncio
    async def test_purchase_deactivated_when_all_paid(self, handler, mocks):
        charge = self._make_charge(installment_number=1)
        purchase = self._make_purchase(num_installments=1)
        account = self._make_account()
        transaction = self._make_transaction()
        paid_charge = self._make_charge(installment_number=1, paid=True)

        mocks["charge_repo"].get_by_uuid = AsyncMock(return_value=charge)
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].create = AsyncMock(return_value=transaction)
        mocks["charge_repo"].update = AsyncMock(return_value=paid_charge)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(return_value=[paid_charge])
        mocks["purchase_repo"].update = AsyncMock()

        await handler.handle(PayInstallmentChargeCommand(
            user_id=1, charge_uuid="charge-uuid-1", payment_date=date.today()
        ))

        assert purchase.is_active is False
        mocks["purchase_repo"].update.assert_called_once_with(purchase)

    @pytest.mark.asyncio
    async def test_purchase_stays_active_with_pending_charges(self, handler, mocks):
        charge = self._make_charge(installment_number=1)
        purchase = self._make_purchase(num_installments=2)
        account = self._make_account()
        transaction = self._make_transaction()
        paid_charge = self._make_charge(installment_number=1, paid=True)
        pending_charge = self._make_charge(installment_number=2, paid=False)

        mocks["charge_repo"].get_by_uuid = AsyncMock(return_value=charge)
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].create = AsyncMock(return_value=transaction)
        mocks["charge_repo"].update = AsyncMock(return_value=paid_charge)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(
            return_value=[paid_charge, pending_charge]
        )
        mocks["purchase_repo"].update = AsyncMock()

        await handler.handle(PayInstallmentChargeCommand(
            user_id=1, charge_uuid="charge-uuid-1", payment_date=date.today()
        ))

        assert purchase.is_active is True
        mocks["purchase_repo"].update.assert_not_called()

    @pytest.mark.asyncio
    async def test_charge_not_found_raises(self, handler, mocks):
        mocks["charge_repo"].get_by_uuid = AsyncMock(return_value=None)

        with pytest.raises(Exception):
            await handler.handle(PayInstallmentChargeCommand(
                user_id=1, charge_uuid="fake-uuid", payment_date=date.today()
            ))

    @pytest.mark.asyncio
    async def test_account_not_found_raises(self, handler, mocks):
        charge = self._make_charge()
        purchase = self._make_purchase()

        mocks["charge_repo"].get_by_uuid = AsyncMock(return_value=charge)
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(PayInstallmentChargeCommand(
                user_id=1, charge_uuid="charge-uuid-1", payment_date=date.today()
            ))

    @pytest.mark.asyncio
    async def test_rejects_charge_from_another_user_without_mutating_state(self, handler, mocks):
        charge = self._make_charge()
        purchase = self._make_purchase()
        purchase.user_id = 2

        mocks["charge_repo"].get_by_uuid = AsyncMock(return_value=charge)
        mocks["purchase_repo"].get_by_id = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock()
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].create = AsyncMock()
        mocks["charge_repo"].update = AsyncMock()

        with pytest.raises(InstallmentChargeNotFoundError):
            await handler.handle(PayInstallmentChargeCommand(
                user_id=1, charge_uuid="charge-uuid-1", payment_date=date.today()
            ))

        mocks["account_repo"].get_by_id.assert_not_called()
        mocks["account_repo"].update.assert_not_called()
        mocks["transaction_repo"].create.assert_not_called()
        mocks["charge_repo"].update.assert_not_called()
