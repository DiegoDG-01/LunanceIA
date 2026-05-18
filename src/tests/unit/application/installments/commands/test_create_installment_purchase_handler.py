import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime, timezone

from application.installments.commands.create_installment_purchase import (
    CreateInstallmentPurchaseCommand,
    CreateInstallmentPurchaseHandler,
)
from application.dto.installment_dto import CreateInstallmentPurchaseDTO
from domain.entities.account import Account
from domain.entities.user import User
from domain.entities.installment_purchase import InstallmentPurchase
from domain.entities.installment_charge import InstallmentCharge
from domain.objects.enums import AccountType, InstallmentType
from domain.objects.money import Money
from shared.exceptions.domain import (
    UserNotFoundError,
    AccountNotFoundError,
    InvalidInstallmentPaymentError,
)


@pytest.mark.unit
class TestCreateInstallmentPurchaseHandler:

    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "user_repo": MagicMock(),
            "account_repo": MagicMock(),
            "purchase_repo": MagicMock(),
            "charge_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return CreateInstallmentPurchaseHandler(
            user_repository=mocks["user_repo"],
            account_repository=mocks["account_repo"],
            installment_purchase_repository=mocks["purchase_repo"],
            installment_charge_repository=mocks["charge_repo"],
            uow=mocks["uow"],
        )

    def _make_user(self, is_active: bool = True) -> User:
        return User(
            id=1, uuid="u-1", auth0_id="a-1", name="Test",
            email="t@t.com", is_active=is_active,
        )

    def _make_credit_card_account(self) -> Account:
        return Account(
            id=10, uuid="acc-uuid-1", user_id=1, bank_id=1,
            name="BBVA TDC", account_type=AccountType.CREDIT_CARD,
            current_balance=Money(Decimal("50000.00")),
            is_active=True, creation_date=datetime.now(timezone.utc),
        )

    def _make_purchase(self, num_installments: int = 12) -> InstallmentPurchase:
        return InstallmentPurchase(
            id=1, uuid="purchase-uuid-1", user_id=1, account_id=10,
            category_id=None, description="iPhone 15 Pro",
            total_amount=Money(Decimal("24000.00")),
            num_installments=num_installments,
            installment_type=InstallmentType.NO_INTEREST,
            annual_interest_rate=Decimal("0"),
            monthly_payment=Decimal("2000.00"),
            purchase_date=date.today(), notes=None,
            is_active=True, creation_date=datetime.now(timezone.utc),
        )

    def _make_charges(self, purchase: InstallmentPurchase):
        return [
            InstallmentCharge(
                id=i, uuid=f"charge-uuid-{i}", installment_purchase_id=1,
                installment_number=i, amount=purchase.monthly_payment,
                due_date=date.today(), paid=False,
                creation_date=datetime.now(timezone.utc),
            )
            for i in range(1, purchase.num_installments + 1)
        ]

    def _make_dto(self, **kwargs) -> CreateInstallmentPurchaseDTO:
        defaults = dict(
            user_id=1, account_uuid="acc-uuid-1", category_id=None,
            description="iPhone 15 Pro", total_amount=Decimal("24000.00"),
            num_installments=12, installment_type=InstallmentType.NO_INTEREST,
            annual_interest_rate=Decimal("0"), purchase_date=date.today(),
        )
        defaults.update(kwargs)
        return CreateInstallmentPurchaseDTO(**defaults)

    @pytest.mark.asyncio
    async def test_create_msi_success(self, handler, mocks):
        user = self._make_user()
        account = self._make_credit_card_account()
        purchase = self._make_purchase()
        charges = self._make_charges(purchase)

        mocks["user_repo"].get_by_id = AsyncMock(return_value=user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["purchase_repo"].create = AsyncMock(return_value=purchase)
        mocks["charge_repo"].create_bulk = AsyncMock(return_value=charges)

        result = await handler.handle(CreateInstallmentPurchaseCommand(dto=self._make_dto()))

        assert result.uuid == "purchase-uuid-1"
        assert result.installment_type == InstallmentType.NO_INTEREST
        assert len(result.charges) == 12
        mocks["purchase_repo"].create.assert_called_once()
        mocks["charge_repo"].create_bulk.assert_called_once()

    @pytest.mark.asyncio
    async def test_balance_is_deducted_at_creation(self, handler, mocks):
        user = self._make_user()
        account = self._make_credit_card_account()
        purchase = self._make_purchase()
        charges = self._make_charges(purchase)

        mocks["user_repo"].get_by_id = AsyncMock(return_value=user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["purchase_repo"].create = AsyncMock(return_value=purchase)
        mocks["charge_repo"].create_bulk = AsyncMock(return_value=charges)

        await handler.handle(CreateInstallmentPurchaseCommand(dto=self._make_dto()))

        # 50000 - 24000 = 26000 (crédito disponible restante)
        assert account.current_balance.amount == Decimal("26000.00")
        mocks["account_repo"].update.assert_called_once_with(account)

    @pytest.mark.asyncio
    async def test_generates_correct_number_of_charges(self, handler, mocks):
        user = self._make_user()
        account = self._make_credit_card_account()
        purchase = self._make_purchase(num_installments=6)
        charges = self._make_charges(purchase)

        mocks["user_repo"].get_by_id = AsyncMock(return_value=user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["purchase_repo"].create = AsyncMock(return_value=purchase)
        mocks["charge_repo"].create_bulk = AsyncMock(return_value=charges)

        await handler.handle(CreateInstallmentPurchaseCommand(
            dto=self._make_dto(num_installments=6)
        ))

        created_charges = mocks["charge_repo"].create_bulk.call_args[0][0]
        assert len(created_charges) == 6

    @pytest.mark.asyncio
    async def test_last_charge_absorbs_rounding(self, handler, mocks):
        user = self._make_user()
        account = self._make_credit_card_account()
        purchase = InstallmentPurchase(
            id=1, uuid="p-1", user_id=1, account_id=10, category_id=None,
            description="Test", total_amount=Money(Decimal("10001.00")),
            num_installments=3, installment_type=InstallmentType.NO_INTEREST,
            annual_interest_rate=Decimal("0"), monthly_payment=Decimal("3333.67"),
            purchase_date=date.today(), notes=None, is_active=True,
            creation_date=datetime.now(timezone.utc),
        )
        charges = self._make_charges(purchase)

        mocks["user_repo"].get_by_id = AsyncMock(return_value=user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["purchase_repo"].create = AsyncMock(return_value=purchase)
        mocks["charge_repo"].create_bulk = AsyncMock(return_value=charges)

        await handler.handle(CreateInstallmentPurchaseCommand(
            dto=self._make_dto(total_amount=Decimal("10001.00"), num_installments=3)
        ))

        created_charges = mocks["charge_repo"].create_bulk.call_args[0][0]
        total = sum(c.amount for c in created_charges)
        assert total == Decimal("10001.00")

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self, handler, mocks):
        mocks["user_repo"].get_by_id = AsyncMock(return_value=None)

        with pytest.raises(UserNotFoundError):
            await handler.handle(CreateInstallmentPurchaseCommand(dto=self._make_dto()))

    @pytest.mark.asyncio
    async def test_inactive_user_raises(self, handler, mocks):
        mocks["user_repo"].get_by_id = AsyncMock(return_value=self._make_user(is_active=False))

        with pytest.raises(UserNotFoundError):
            await handler.handle(CreateInstallmentPurchaseCommand(dto=self._make_dto()))

    @pytest.mark.asyncio
    async def test_account_not_found_raises(self, handler, mocks):
        mocks["user_repo"].get_by_id = AsyncMock(return_value=self._make_user())
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(CreateInstallmentPurchaseCommand(dto=self._make_dto()))

    @pytest.mark.asyncio
    async def test_non_credit_card_account_raises(self, handler, mocks):
        user = self._make_user()
        checking_account = Account(
            id=10, uuid="acc-uuid-1", user_id=1, bank_id=1,
            name="Débito", account_type=AccountType.CHECKING,
            current_balance=Money(Decimal("10000.00")),
            is_active=True, creation_date=datetime.now(timezone.utc),
        )
        mocks["user_repo"].get_by_id = AsyncMock(return_value=user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=checking_account)

        with pytest.raises(InvalidInstallmentPaymentError):
            await handler.handle(CreateInstallmentPurchaseCommand(dto=self._make_dto()))
