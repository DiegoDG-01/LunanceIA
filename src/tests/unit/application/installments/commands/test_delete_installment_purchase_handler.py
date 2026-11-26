from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.installments.commands.delete_installment_purchase import (
    DeleteInstallmentPurchaseCommand,
    DeleteInstallmentPurchaseHandler,
)
from domain.entities.accounts.account import Account
from domain.entities.installments.installment_charge import InstallmentCharge
from domain.entities.installments.installment_purchase import InstallmentPurchase
from domain.entities.transactions.transaction import Transaction
from domain.objects.enums import AccountType, InstallmentType, TransactionType
from domain.objects.money import Money
from shared.exceptions.domain import (
    AccountNotFoundError,
    BulkDeleteFailedError,
    InstallmentPurchaseNotFoundError,
)


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

    def _make_account(
        self,
        account_id: int = 10,
        balance: Decimal = Decimal("38000.00"),
        account_type: AccountType = AccountType.CREDIT_CARD,
    ) -> Account:
        # En la TDC, balance = crédito disponible. Ej: límite 50,000 - compra 12,000
        return Account(
            id=account_id,
            uuid=f"acc-uuid-{account_id}",
            user_id=1,
            bank_id=1,
            name="BBVA TDC" if account_id == 10 else "Nómina",
            account_type=account_type,
            current_balance=Money(balance),
            is_active=True,
            creation_date=datetime.now(UTC),
        )

    def _make_card(self, balance: Decimal) -> Account:
        return self._make_account(10, balance)

    def _make_source(self, balance: Decimal) -> Account:
        return self._make_account(5, balance, AccountType.CHECKING)

    def _make_purchase(
        self,
        total: Decimal = Decimal("12000.00"),
        initial_transaction_id: int | None = 99,
    ) -> InstallmentPurchase:
        purchase = InstallmentPurchase(
            id=1,
            uuid="purchase-uuid-1",
            user_id=1,
            account_id=10,
            category_id=1,
            description="iPhone 15 Pro",
            total_amount=Money(total),
            num_installments=12,
            installment_type=InstallmentType.NO_INTEREST,
            annual_interest_rate=Decimal(0),
            monthly_payment=Decimal("1000.00"),
            purchase_date=date.today(),
            notes=None,
            is_active=True,
            creation_date=datetime.now(UTC),
        )
        purchase.initial_transaction_id = initial_transaction_id
        return purchase

    @staticmethod
    def _incoming_id(number: int) -> int:
        return 100 + number * 10 + 1

    @staticmethod
    def _outgoing_id(number: int) -> int:
        return 100 + number * 10

    def _make_charge(self, number: int, paid: bool = False) -> InstallmentCharge:
        return InstallmentCharge(
            id=number,
            uuid=f"charge-uuid-{number}",
            installment_purchase_id=1,
            installment_number=number,
            amount=Decimal("1000.00"),
            due_date=date.today(),
            paid=paid,
            transaction_id=self._incoming_id(number) if paid else None,
            creation_date=datetime.now(UTC),
        )

    def _make_transaction(
        self,
        tx_id: int,
        account_id: int,
        tx_type: TransactionType,
        amount: Decimal,
        transfer_uuid: str | None = None,
    ) -> Transaction:
        return Transaction(
            id=tx_id,
            uuid=f"tx-uuid-{tx_id}",
            user_id=1,
            account_id=account_id,
            category_id=None,
            transaction_type=tx_type,
            amount=Money(amount),
            transaction_date=date.today(),
            transfer_uuid=transfer_uuid,
            creation_date=datetime.now(UTC),
        )

    def _setup(self, mocks, purchase, card, charges, source=None):
        """Arma el modelo nuevo: gasto inicial + una transferencia por cuota pagada."""
        transactions = {
            99: self._make_transaction(
                99, 10, TransactionType.EXPENSE, purchase.total_amount.amount
            )
        }
        transfers = {}
        for charge in charges:
            if not charge.paid:
                continue
            n = charge.installment_number
            uuid = f"transfer-{n}"
            outgoing = self._make_transaction(
                self._outgoing_id(n), 5, TransactionType.TRANSFER, charge.amount, uuid
            )
            incoming = self._make_transaction(
                self._incoming_id(n), 10, TransactionType.TRANSFER, charge.amount, uuid
            )
            transactions[incoming.id] = incoming
            transfers[uuid] = [outgoing, incoming]

        accounts = {10: card}
        if source is not None:
            accounts[5] = source

        mocks["purchase_repo"].get_by_uuid = AsyncMock(return_value=purchase)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(return_value=charges)
        mocks["transaction_repo"].get_by_id = AsyncMock(
            side_effect=lambda tx_id, for_update=False: transactions.get(tx_id)
        )
        mocks["transaction_repo"].get_by_transfer_uuid = AsyncMock(
            side_effect=lambda uuid, user_id, for_update=False: transfers[uuid]
        )
        mocks["account_repo"].get_by_id = AsyncMock(
            side_effect=lambda account_id, for_update=False: accounts.get(account_id)
        )
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].delete_bulk_by_ids = AsyncMock(return_value=True)
        mocks["charge_repo"].delete_by_purchase_id = AsyncMock()
        mocks["purchase_repo"].delete = AsyncMock()

    async def _delete(self, handler):
        await handler.handle(
            DeleteInstallmentPurchaseCommand(user_id=1, purchase_uuid="purchase-uuid-1")
        )

    def _deleted_ids(self, mocks) -> list[int]:
        kwargs = mocks["transaction_repo"].delete_bulk_by_ids.await_args.kwargs
        return sorted(kwargs["transaction_ids"])

    # --- Balance ---

    @pytest.mark.asyncio
    async def test_no_paid_charges_restores_full_total(self, handler, mocks):
        # 50,000 - 12,000 (compra) = 38,000
        card = self._make_card(Decimal("38000.00"))
        charges = [self._make_charge(i) for i in range(1, 5)]
        self._setup(mocks, self._make_purchase(), card, charges)

        await self._delete(handler)

        assert card.current_balance.amount == Decimal("50000.00")

    @pytest.mark.asyncio
    async def test_partial_payments_restore_total_minus_paid(self, handler, mocks):
        # 50,000 - 12,000 (compra) + 3,000 (3 pagos) = 41,000
        card = self._make_card(Decimal("41000.00"))
        source = self._make_source(Decimal("1000.00"))
        charges = [
            self._make_charge(1, paid=True),
            self._make_charge(2, paid=True),
            self._make_charge(3, paid=True),
            self._make_charge(4),
        ]
        self._setup(mocks, self._make_purchase(), card, charges, source)

        await self._delete(handler)

        assert card.current_balance.amount == Decimal("50000.00")
        # La cuenta origen recupera los 3,000 que pagó
        assert source.current_balance.amount == Decimal("4000.00")

    @pytest.mark.asyncio
    async def test_all_charges_paid_leaves_card_unchanged(self, handler, mocks):
        # 50,000 - 3,000 (compra) + 3,000 (todos pagados) = 50,000
        card = self._make_card(Decimal("50000.00"))
        source = self._make_source(Decimal("0.00"))
        charges = [self._make_charge(i, paid=True) for i in range(1, 4)]
        purchase = self._make_purchase(total=Decimal("3000.00"))
        self._setup(mocks, purchase, card, charges, source)

        await self._delete(handler)

        assert card.current_balance.amount == Decimal("50000.00")
        assert source.current_balance.amount == Decimal("3000.00")

    # --- Transacciones ---

    @pytest.mark.asyncio
    async def test_deletes_initial_expense_and_both_legs_of_each_transfer(
        self, handler, mocks
    ):
        card = self._make_card(Decimal("39000.00"))
        source = self._make_source(Decimal("1000.00"))
        charges = [
            self._make_charge(1, paid=True),
            self._make_charge(2, paid=True),
            self._make_charge(3),
        ]
        self._setup(mocks, self._make_purchase(), card, charges, source)

        await self._delete(handler)

        mocks["transaction_repo"].delete_bulk_by_ids.assert_awaited_once()
        assert self._deleted_ids(mocks) == [99, 110, 111, 120, 121]

    @pytest.mark.asyncio
    async def test_only_initial_expense_deleted_when_none_paid(self, handler, mocks):
        card = self._make_card(Decimal("38000.00"))
        charges = [self._make_charge(i) for i in range(1, 4)]
        self._setup(mocks, self._make_purchase(), card, charges)

        await self._delete(handler)

        assert self._deleted_ids(mocks) == [99]
        mocks["transaction_repo"].get_by_transfer_uuid.assert_not_called()

    # --- Eliminación de registros ---

    @pytest.mark.asyncio
    async def test_charges_and_purchase_are_deleted_then_committed(
        self, handler, mocks
    ):
        card = self._make_card(Decimal("38000.00"))
        self._setup(mocks, self._make_purchase(), card, [self._make_charge(1)])

        await self._delete(handler)

        mocks["charge_repo"].delete_by_purchase_id.assert_called_once_with(
            purchase_id=1
        )
        mocks["purchase_repo"].delete.assert_called_once_with(
            purchase_uuid="purchase-uuid-1"
        )
        mocks["uow"].commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_every_touched_account_is_saved(self, handler, mocks):
        card = self._make_card(Decimal("41000.00"))
        source = self._make_source(Decimal("1000.00"))
        charges = [self._make_charge(1, paid=True)]
        self._setup(mocks, self._make_purchase(), card, charges, source)

        await self._delete(handler)

        saved = [call.args[0] for call in mocks["account_repo"].update.await_args_list]
        assert sorted(a.id for a in saved) == [5, 10]

    # --- Errores ---

    @pytest.mark.asyncio
    async def test_purchase_not_found_raises(self, handler, mocks):
        mocks["purchase_repo"].get_by_uuid = AsyncMock(return_value=None)

        with pytest.raises(InstallmentPurchaseNotFoundError):
            await self._delete(handler)

    @pytest.mark.asyncio
    async def test_purchase_without_initial_transaction_is_rejected(
        self, handler, mocks
    ):
        # Compra del modelo anterior (o con el vínculo perdido): no se borra a ciegas
        card = self._make_card(Decimal("38000.00"))
        purchase = self._make_purchase(initial_transaction_id=None)
        self._setup(mocks, purchase, card, [self._make_charge(1)])

        with pytest.raises(BulkDeleteFailedError):
            await self._delete(handler)

        mocks["account_repo"].update.assert_not_called()
        mocks["transaction_repo"].delete_bulk_by_ids.assert_not_called()
        mocks["charge_repo"].delete_by_purchase_id.assert_not_called()
        mocks["purchase_repo"].delete.assert_not_called()
        mocks["uow"].commit.assert_not_awaited()
        assert card.current_balance.amount == Decimal("38000.00")

    @pytest.mark.asyncio
    async def test_missing_initial_transaction_raises(self, handler, mocks):
        card = self._make_card(Decimal("38000.00"))
        self._setup(mocks, self._make_purchase(), card, [self._make_charge(1)])
        mocks["transaction_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(BulkDeleteFailedError):
            await self._delete(handler)

        mocks["purchase_repo"].delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_transfer_without_two_legs_raises(self, handler, mocks):
        card = self._make_card(Decimal("39000.00"))
        source = self._make_source(Decimal("1000.00"))
        charges = [self._make_charge(1, paid=True)]
        self._setup(mocks, self._make_purchase(), card, charges, source)
        mocks["transaction_repo"].get_by_transfer_uuid = AsyncMock(return_value=[])

        with pytest.raises(BulkDeleteFailedError):
            await self._delete(handler)

        mocks["account_repo"].update.assert_not_called()
        mocks["uow"].commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_account_not_found_raises(self, handler, mocks):
        card = self._make_card(Decimal("38000.00"))
        self._setup(mocks, self._make_purchase(), card, [self._make_charge(1)])
        mocks["account_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(AccountNotFoundError):
            await self._delete(handler)

        mocks["uow"].commit.assert_not_awaited()
