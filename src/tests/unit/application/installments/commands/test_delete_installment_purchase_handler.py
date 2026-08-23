import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime, timezone

from application.installments.commands.delete_installment_purchase import (
    DeleteInstallmentPurchaseCommand,
    DeleteInstallmentPurchaseHandler,
)
from domain.entities.account import Account
from domain.entities.installment_charge import InstallmentCharge
from domain.entities.installment_purchase import InstallmentPurchase
from domain.entities.transaction import Transaction
from domain.objects.enums import AccountType, InstallmentType, TransactionType
from domain.objects.money import Money
from shared.exceptions.domain import AccountNotFoundError


@pytest.mark.unit
class TestDeleteInstallmentPurchaseHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "account_repo": MagicMock(),
            "transaction_repo": MagicMock(),
            "purchase_repo": MagicMock(),
            "charge_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return DeleteInstallmentPurchaseHandler(
            account_repository=mocks["account_repo"],
            transaction_repository=mocks["transaction_repo"],
            installment_purchase_repository=mocks["purchase_repo"],
            installment_charge_repository=mocks["charge_repo"],
            uow=mocks["uow"],
        )

    def _make_account(self, balance: Decimal = Decimal("38000.00")) -> Account:
        # Balance = crédito disponible. Ej: límite $50,000 - compra $12,000 = $38,000
        return Account(
            id=10,
            uuid="acc-uuid-1",
            user_id=1,
            bank_id=1,
            name="BBVA TDC",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Money(balance),
            is_active=True,
            creation_date=datetime.now(timezone.utc),
        )

    def _make_purchase(
        self, total: Decimal = Decimal("12000.00")
    ) -> InstallmentPurchase:
        return InstallmentPurchase(
            id=1,
            uuid="purchase-uuid-1",
            user_id=1,
            account_id=10,
            category_id=1,
            description="iPhone 15 Pro",
            total_amount=Money(total),
            num_installments=12,
            installment_type=InstallmentType.NO_INTEREST,
            annual_interest_rate=Decimal("0"),
            monthly_payment=Decimal("1000.00"),
            purchase_date=date.today(),
            notes=None,
            is_active=True,
            creation_date=datetime.now(timezone.utc),
        )

    def _make_charge(
        self, number: int, paid: bool = False, transaction_id=None
    ) -> InstallmentCharge:
        return InstallmentCharge(
            id=number,
            uuid=f"charge-uuid-{number}",
            installment_purchase_id=1,
            installment_number=number,
            amount=Decimal("1000.00"),
            due_date=date.today(),
            paid=paid,
            transaction_id=transaction_id,
            creation_date=datetime.now(timezone.utc),
        )

    def _make_transaction(self, tx_id: int) -> Transaction:
        return Transaction(
            id=tx_id,
            uuid=f"tx-uuid-{tx_id}",
            user_id=1,
            account_id=10,
            category_id=None,
            transaction_type=TransactionType.EXPENSE,
            amount=Money(Decimal("1000.00")),
            transaction_date=date.today(),
            creation_date=datetime.now(timezone.utc),
        )

    def _setup_base_mocks(self, mocks, purchase, account, charges):
        mocks["purchase_repo"].get_by_uuid = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(return_value=charges)
        mocks["account_repo"].update = AsyncMock()
        mocks["charge_repo"].delete_by_purchase_id = AsyncMock()
        mocks["purchase_repo"].delete = AsyncMock()

    # --- Balance ---

    @pytest.mark.asyncio
    async def test_balance_restored_with_no_paid_charges(self, handler, mocks):
        purchase = self._make_purchase(total=Decimal("12000.00"))
        account = self._make_account(balance=Decimal("38000.00"))
        charges = [self._make_charge(i) for i in range(1, 4)]

        self._setup_base_mocks(mocks, purchase, account, charges)

        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

        # net_restore = 12000 - 0 = 12000 → 38000 + 12000 = 50000
        assert account.current_balance.amount == Decimal("50000.00")

    @pytest.mark.asyncio
    async def test_balance_restored_with_partial_payments(self, handler, mocks):
        purchase = self._make_purchase(total=Decimal("12000.00"))
        # balance actual: 50000 - 12000 (compra) + 3000 (3 pagos) = 41000
        account = self._make_account(balance=Decimal("41000.00"))
        charges = [
            self._make_charge(1, paid=True, transaction_id=101),
            self._make_charge(2, paid=True, transaction_id=102),
            self._make_charge(3, paid=True, transaction_id=103),
            self._make_charge(4, paid=False),
        ]
        self._setup_base_mocks(mocks, purchase, account, charges)
        mocks["transaction_repo"].delete_bulk_by_ids = AsyncMock(return_value=True)

        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

        # net_restore = 12000 - 3000 = 9000 → 41000 + 9000 = 50000
        assert account.current_balance.amount == Decimal("50000.00")

    @pytest.mark.asyncio
    async def test_balance_unchanged_when_all_charges_paid(self, handler, mocks):
        purchase = self._make_purchase(total=Decimal("3000.00"))
        # balance actual: 50000 - 3000 (compra) + 3000 (todos pagados) = 50000
        account = self._make_account(balance=Decimal("50000.00"))
        charges = [
            self._make_charge(i, paid=True, transaction_id=100 + i) for i in range(1, 4)
        ]
        self._setup_base_mocks(mocks, purchase, account, charges)
        mocks["transaction_repo"].delete_bulk_by_ids = AsyncMock(return_value=True)

        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

        # net_restore = 3000 - 3000 = 0 → balance no cambia
        assert account.current_balance.amount == Decimal("50000.00")

    @pytest.mark.asyncio
    async def test_new_purchase_deletion_reverts_initial_expense_and_payment_transfer(
        self, handler, mocks
    ):
        purchase = self._make_purchase()
        purchase.initial_transaction_id = 99
        card = self._make_account(balance=Decimal("39000.00"))
        source = Account(
            id=5,
            uuid="checking-uuid",
            user_id=1,
            bank_id=1,
            name="Nómina",
            account_type=AccountType.CHECKING,
            current_balance=Money(Decimal("1000.00")),
            is_active=True,
            creation_date=datetime.now(timezone.utc),
        )
        charges = [self._make_charge(1, paid=True, transaction_id=101)]
        initial = Transaction(
            id=99,
            uuid="initial-uuid",
            user_id=1,
            account_id=10,
            category_id=1,
            transaction_type=TransactionType.EXPENSE,
            amount=Money(Decimal("12000.00")),
            transaction_date=date.today(),
            creation_date=datetime.now(timezone.utc),
        )
        outgoing = Transaction(
            id=100,
            uuid="outgoing-uuid",
            user_id=1,
            account_id=5,
            category_id=None,
            transaction_type=TransactionType.TRANSFER,
            amount=Money(Decimal("1000.00")),
            transaction_date=date.today(),
            transfer_uuid="transfer-uuid",
            creation_date=datetime.now(timezone.utc),
        )
        incoming = Transaction(
            id=101,
            uuid="incoming-uuid",
            user_id=1,
            account_id=10,
            category_id=None,
            transaction_type=TransactionType.TRANSFER,
            amount=Money(Decimal("1000.00")),
            transaction_date=date.today(),
            transfer_uuid="transfer-uuid",
            creation_date=datetime.now(timezone.utc),
        )
        mocks["purchase_repo"].get_by_uuid = AsyncMock(return_value=purchase)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(return_value=charges)
        mocks["transaction_repo"].get_by_id = AsyncMock(side_effect=[initial, incoming])
        mocks["transaction_repo"].get_by_transfer_uuid = AsyncMock(
            return_value=[outgoing, incoming]
        )
        mocks["account_repo"].get_by_id = AsyncMock(
            side_effect=lambda account_id, for_update: {5: source, 10: card}[account_id]
        )
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].delete_bulk_by_ids = AsyncMock(return_value=True)
        mocks["charge_repo"].delete_by_purchase_id = AsyncMock()
        mocks["purchase_repo"].delete = AsyncMock()

        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

        assert card.current_balance.amount == Decimal("50000.00")
        assert source.current_balance.amount == Decimal("2000.00")
        mocks["transaction_repo"].delete_bulk_by_ids.assert_awaited_once_with(
            transaction_ids=[99, 100, 101], user_id=1
        )

    # --- Transacciones ---

    @pytest.mark.asyncio
    async def test_transactions_deleted_for_each_paid_charge(self, handler, mocks):
        purchase = self._make_purchase()
        account = self._make_account()
        charges = [
            self._make_charge(1, paid=True, transaction_id=101),
            self._make_charge(2, paid=True, transaction_id=102),
            self._make_charge(3, paid=False),
        ]
        self._setup_base_mocks(mocks, purchase, account, charges)
        mocks["transaction_repo"].delete_bulk_by_ids = AsyncMock(return_value=True)

        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

        mocks["transaction_repo"].delete_bulk_by_ids.assert_called_once_with(
            transaction_ids=[101, 102], user_id=1
        )

    @pytest.mark.asyncio
    async def test_no_transactions_deleted_when_none_paid(self, handler, mocks):
        purchase = self._make_purchase()
        account = self._make_account()
        charges = [self._make_charge(i) for i in range(1, 4)]

        self._setup_base_mocks(mocks, purchase, account, charges)
        mocks["transaction_repo"].delete_bulk_by_ids = AsyncMock(return_value=True)

        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

        mocks["transaction_repo"].delete_bulk_by_ids.assert_not_called()

    # --- Eliminación de registros ---

    @pytest.mark.asyncio
    async def test_charges_deleted_by_purchase_id(self, handler, mocks):
        purchase = self._make_purchase()
        account = self._make_account()
        charges = [self._make_charge(1)]
        self._setup_base_mocks(mocks, purchase, account, charges)

        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

        mocks["charge_repo"].delete_by_purchase_id.assert_called_once_with(
            purchase_id=1
        )

    @pytest.mark.asyncio
    async def test_purchase_deleted_by_uuid(self, handler, mocks):
        purchase = self._make_purchase()
        account = self._make_account()
        charges = [self._make_charge(1)]
        self._setup_base_mocks(mocks, purchase, account, charges)

        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

        mocks["purchase_repo"].delete.assert_called_once_with(
            purchase_uuid="purchase-uuid-1"
        )

    @pytest.mark.asyncio
    async def test_account_balance_updated(self, handler, mocks):
        purchase = self._make_purchase()
        account = self._make_account()
        charges = [self._make_charge(1)]
        self._setup_base_mocks(mocks, purchase, account, charges)

        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

        mocks["account_repo"].update.assert_called_once_with(account)

    # --- Errores ---

    @pytest.mark.asyncio
    async def test_purchase_not_found_raises(self, handler, mocks):
        mocks["purchase_repo"].get_by_uuid = AsyncMock(return_value=None)

        with pytest.raises(Exception):
            await handler.handle(
                DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="fake-uuid")
            )

    @pytest.mark.asyncio
    async def test_account_not_found_raises(self, handler, mocks):
        purchase = self._make_purchase()
        mocks["purchase_repo"].get_by_uuid = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=None)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(return_value=[])

        with pytest.raises(AccountNotFoundError):
            await handler.handle(
                DeleteInstallmentPurchaseCommand(
                    user_id=1, purchase_uuid="purchase-uuid-1"
                )
            )
