import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime, timezone

from application.installments.commands.update_installment_purchase import (
    UpdateInstallmentPurchaseCommand,
    UpdateInstallmentPurchaseHandler,
)
from domain.entities.account import Account
from domain.entities.installment_charge import InstallmentCharge
from domain.entities.installment_purchase import InstallmentPurchase
from domain.objects.enums import AccountType, InstallmentType
from domain.objects.money import Money
from shared.exceptions.domain import AccountNotFoundError


@pytest.mark.unit
class TestUpdateInstallmentPurchaseHandler:

    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "account_repo": MagicMock(),
            "purchase_repo": MagicMock(),
            "charge_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return UpdateInstallmentPurchaseHandler(
            account_repository=mocks["account_repo"],
            installment_purchase_repository=mocks["purchase_repo"],
            installment_charge_repository=mocks["charge_repo"],
            uow=mocks["uow"],
        )

    def _make_account(self) -> Account:
        return Account(
            id=10, uuid="acc-uuid-1", user_id=1, bank_id=1,
            name="BBVA TDC", account_type=AccountType.CREDIT_CARD,
            current_balance=Money(Decimal("38000.00")),
            is_active=True, creation_date=datetime.now(timezone.utc),
        )

    def _make_purchase(self) -> InstallmentPurchase:
        return InstallmentPurchase(
            id=1, uuid="purchase-uuid-1", user_id=1, account_id=10,
            category_id=1, description="Descripción original",
            total_amount=Money(Decimal("12000.00")),
            num_installments=12,
            installment_type=InstallmentType.NO_INTEREST,
            annual_interest_rate=Decimal("0"),
            monthly_payment=Decimal("1000.00"),
            purchase_date=date.today(), notes="Notas originales",
            is_active=True, creation_date=datetime.now(timezone.utc),
        )

    def _make_charge(self, number: int) -> InstallmentCharge:
        return InstallmentCharge(
            id=number, uuid=f"charge-uuid-{number}",
            installment_purchase_id=1, installment_number=number,
            amount=Decimal("1000.00"), due_date=date.today(),
            paid=False, creation_date=datetime.now(timezone.utc),
        )

    def _setup_base_mocks(self, mocks, purchase, account):
        mocks["purchase_repo"].get_by_uuid = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["purchase_repo"].update = AsyncMock(return_value=purchase)
        mocks["charge_repo"].get_by_purchase_id = AsyncMock(
            return_value=[self._make_charge(i) for i in range(1, 4)]
        )

    # --- Actualización de campos ---

    @pytest.mark.asyncio
    async def test_update_description(self, handler, mocks):
        purchase = self._make_purchase()
        self._setup_base_mocks(mocks, purchase, self._make_account())

        await handler.handle(UpdateInstallmentPurchaseCommand(
            user_id=1, purchase_uuid="purchase-uuid-1",
            description="Nueva descripción",
        ))

        assert purchase.description == "Nueva descripción"

    @pytest.mark.asyncio
    async def test_update_notes(self, handler, mocks):
        purchase = self._make_purchase()
        self._setup_base_mocks(mocks, purchase, self._make_account())

        await handler.handle(UpdateInstallmentPurchaseCommand(
            user_id=1, purchase_uuid="purchase-uuid-1",
            notes="Nuevas notas",
        ))

        assert purchase.notes == "Nuevas notas"

    @pytest.mark.asyncio
    async def test_update_category_id(self, handler, mocks):
        purchase = self._make_purchase()
        self._setup_base_mocks(mocks, purchase, self._make_account())

        await handler.handle(UpdateInstallmentPurchaseCommand(
            user_id=1, purchase_uuid="purchase-uuid-1",
            category_id=5,
        ))

        assert purchase.category_id == 5

    @pytest.mark.asyncio
    async def test_none_fields_do_not_overwrite_existing_values(self, handler, mocks):
        purchase = self._make_purchase()
        self._setup_base_mocks(mocks, purchase, self._make_account())

        await handler.handle(UpdateInstallmentPurchaseCommand(
            user_id=1, purchase_uuid="purchase-uuid-1",
            description=None, notes=None, category_id=None,
        ))

        assert purchase.description == "Descripción original"
        assert purchase.notes == "Notas originales"
        assert purchase.category_id == 1

    @pytest.mark.asyncio
    async def test_update_multiple_fields_at_once(self, handler, mocks):
        purchase = self._make_purchase()
        self._setup_base_mocks(mocks, purchase, self._make_account())

        await handler.handle(UpdateInstallmentPurchaseCommand(
            user_id=1, purchase_uuid="purchase-uuid-1",
            description="Nueva descripción",
            notes="Nuevas notas",
            category_id=7,
        ))

        assert purchase.description == "Nueva descripción"
        assert purchase.notes == "Nuevas notas"
        assert purchase.category_id == 7

    # --- Respuesta ---

    @pytest.mark.asyncio
    async def test_returns_updated_purchase_with_charges(self, handler, mocks):
        purchase = self._make_purchase()
        self._setup_base_mocks(mocks, purchase, self._make_account())

        result = await handler.handle(UpdateInstallmentPurchaseCommand(
            user_id=1, purchase_uuid="purchase-uuid-1",
            description="Nueva descripción",
        ))

        assert result.uuid == "purchase-uuid-1"
        assert len(result.charges) == 3

    @pytest.mark.asyncio
    async def test_balance_not_modified_on_update(self, handler, mocks):
        purchase = self._make_purchase()
        account = self._make_account()
        self._setup_base_mocks(mocks, purchase, account)
        original_balance = account.current_balance.amount

        await handler.handle(UpdateInstallmentPurchaseCommand(
            user_id=1, purchase_uuid="purchase-uuid-1",
            description="Nueva descripción",
        ))

        assert account.current_balance.amount == original_balance

    # --- Persistencia ---

    @pytest.mark.asyncio
    async def test_repository_update_called(self, handler, mocks):
        purchase = self._make_purchase()
        self._setup_base_mocks(mocks, purchase, self._make_account())

        await handler.handle(UpdateInstallmentPurchaseCommand(
            user_id=1, purchase_uuid="purchase-uuid-1",
            description="Nueva descripción",
        ))

        mocks["purchase_repo"].update.assert_called_once_with(purchase)

    # --- Errores ---

    @pytest.mark.asyncio
    async def test_purchase_not_found_raises(self, handler, mocks):
        mocks["purchase_repo"].get_by_uuid = AsyncMock(return_value=None)

        with pytest.raises(Exception):
            await handler.handle(UpdateInstallmentPurchaseCommand(
                user_id=1, purchase_uuid="fake-uuid",
            ))

    @pytest.mark.asyncio
    async def test_account_not_found_raises(self, handler, mocks):
        purchase = self._make_purchase()
        mocks["purchase_repo"].get_by_uuid = AsyncMock(return_value=purchase)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(UpdateInstallmentPurchaseCommand(
                user_id=1, purchase_uuid="purchase-uuid-1",
            ))
