from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, desc, select
from typing import Optional, List, Tuple

from domain.entities.transaction import Transaction
from domain.repositories.transaction_repository import TransactionRepository
from domain.objects.money import Money
from domain.objects.enums import TransactionType, AccountType
from infrastructure.database.models.transaction import TransactionModel
from infrastructure.database.models.account import AccountModel
from infrastructure.database.models.category import CategoryModel


class SQLAlchemyTransactionRepository(TransactionRepository):
    """Implementación SQLAlchemy del repositorio de transacciones."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _models_to_entity_with_account(
        self,
        transaction_model: TransactionModel,
        account_model: AccountModel,
        category_model: CategoryModel,
        bank_name: Optional[str] = None,
    ) -> tuple[Transaction, str, AccountType, Optional[str], Optional[str]]:
        transaction = self._model_to_entity(transaction_model)
        category_name = category_model.name if category_model else None
        return (
            transaction,
            account_model.name,
            account_model.type,
            bank_name,
            category_name,
        )

    def _model_to_entity(self, model: TransactionModel) -> Transaction:
        """Convierte modelo SQLAlchemy a entidad de dominio."""
        return Transaction(
            id=model.id,
            uuid=model.uuid,
            user_id=model.user_id,
            account_id=model.account_id,
            transaction_type=model.type,
            amount=Money(amount=model.amount, currency="MXN"),  # Asumo MXN por defecto
            transaction_date=model.transaction_date,
            description=model.description,
            notes=model.notes,
            creation_date=model.creation_date,
            category_id=model.category_id,
        )

    def _entity_to_model(self, entity: Transaction) -> TransactionModel:
        """Convierte entidad de dominio a modelo SQLAlchemy."""
        return TransactionModel(
            uuid=entity.uuid,
            user_id=entity.user_id,
            account_id=entity.account_id,
            category_id=entity.category_id,
            type=entity.transaction_type,
            amount=entity.amount.amount,
            transaction_date=entity.transaction_date,
            description=entity.description,
            notes=entity.notes,
            creation_date=entity.creation_date,
        )

    async def create(self, transaction: Transaction) -> Transaction:
        """Crea una nueva transacción."""
        model = self._entity_to_model(transaction)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Obtiene transacción por ID."""
        stmt = select(TransactionModel).where(TransactionModel.id == transaction_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_id_and_user_uuid(
        self, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """Obtiene transacción por ID y UUID del usuario."""
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.id == transaction_id,
                TransactionModel.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_id_and_user(
        self, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """Obtiene transacción que pertenezca al usuario especificado."""
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.id == transaction_id,
                TransactionModel.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_user(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Tuple[Transaction, str, AccountType, Optional[str], Optional[str]]]:
        """Obtiene todas las transacciones de un usuario con paginación."""
        stmt = (
            select(TransactionModel, AccountModel, CategoryModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .outerjoin(CategoryModel, TransactionModel.category_id == CategoryModel.id)
            .where(TransactionModel.user_id == user_id)
            .order_by(desc(TransactionModel.creation_date))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        results = result.all()

        return [
            self._models_to_entity_with_account(transaction, acc, cat)
            for transaction, acc, cat in results
        ]

    async def get_by_account(
        self, account_id: int, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Obtiene todas las transacciones de una cuenta específica."""
        stmt = (
            select(TransactionModel)
            .where(
                and_(
                    TransactionModel.account_id == account_id,
                    TransactionModel.user_id == user_id,
                )
            )
            .order_by(desc(TransactionModel.creation_date))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_date_range(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_uuid: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
    ) -> List[Tuple[Transaction, str, AccountType, Optional[str], Optional[str]]]:
        """Obtiene transacciones en un rango de fechas."""
        stmt = (
            select(TransactionModel, AccountModel, CategoryModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .outerjoin(CategoryModel, TransactionModel.category_id == CategoryModel.id)
            .where(TransactionModel.user_id == user_id)
        )

        if start_date:
            stmt = stmt.where(TransactionModel.transaction_date >= start_date)

        if end_date:
            stmt = stmt.where(TransactionModel.transaction_date <= end_date)

        if account_uuid:
            stmt = stmt.where(AccountModel.uuid == account_uuid)

        if transaction_type:
            stmt = stmt.where(TransactionModel.type == transaction_type)

        stmt = stmt.order_by(desc(TransactionModel.transaction_date))
        result = await self.db.execute(stmt)
        results = result.all()

        return [
            self._models_to_entity_with_account(transaction, acc, cat)
            for transaction, acc, cat in results
        ]

    async def get_by_category(
        self,
        user_id: int,
        category_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Transaction]:
        """Obtiene transacciones por categoría."""
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.user_id == user_id,
                TransactionModel.category_id == category_id,
            )
        )

        if start_date:
            stmt = stmt.where(TransactionModel.transaction_date >= start_date)

        if end_date:
            stmt = stmt.where(TransactionModel.transaction_date <= end_date)

        stmt = stmt.order_by(desc(TransactionModel.transaction_date))
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_uuid_with_account_details(
        self, uuid: str, user_id: int
    ) -> Optional[Tuple[Transaction, str, AccountType, Optional[str], Optional[str]]]:
        stmt = (
            select(TransactionModel, AccountModel, CategoryModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .outerjoin(CategoryModel, TransactionModel.category_id == CategoryModel.id)
            .where(
                and_(TransactionModel.uuid == uuid, TransactionModel.user_id == user_id)
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()

        if not row:
            return None

        transaction_model, account_model, category_model = row
        return self._models_to_entity_with_account(
            transaction_model, account_model, category_model
        )

    async def get_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """Obtiene transacciones por tipo (ingreso/gasto)."""
        stmt = (
            select(TransactionModel)
            .where(
                and_(
                    TransactionModel.user_id == user_id,
                    TransactionModel.type == transaction_type,
                )
            )
            .order_by(desc(TransactionModel.creation_date))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def update(self, transaction: Transaction) -> Transaction:
        """Actualiza una transacción."""
        stmt = select(TransactionModel).where(TransactionModel.uuid == transaction.uuid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError("Transacción no encontrada")

        # Actualizar campos
        # Set category_id in all cases
        # Case 1: category_id is not None and exists id for that category
        # Case 2: category_id is None and no category exists or user not set category
        model.category_id = transaction.category_id

        if transaction.transaction_type is not None:
            model.type = transaction.transaction_type
        if transaction.amount is not None:
            model.amount = transaction.amount.amount
        if transaction.transaction_date is not None:
            model.transaction_date = transaction.transaction_date
        if transaction.description is not None:
            model.description = transaction.description
        if transaction.notes is not None:
            model.notes = transaction.notes

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete_by_uuid(self, uuid: str, user_id: int) -> bool:
        """Elimina una transacción."""
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.uuid == uuid,
                TransactionModel.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self.db.delete(model)
            await self.db.flush()
            return True

        return False

    async def get_total_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_id: Optional[int] = None,
    ) -> float:
        """Obtiene el total de transacciones por tipo en un período."""
        stmt = select(func.sum(TransactionModel.amount)).where(
            and_(
                TransactionModel.user_id == user_id,
                TransactionModel.type == transaction_type,
            )
        )

        if start_date:
            stmt = stmt.where(TransactionModel.transaction_date >= start_date)

        if end_date:
            stmt = stmt.where(TransactionModel.transaction_date <= end_date)

        if account_id:
            stmt = stmt.where(TransactionModel.account_id == account_id)

        result = await self.db.execute(stmt)
        total = result.scalar()
        return float(total) if total else 0.0

    async def get_monthly_summary(
        self, user_id: int, year: int, month: int, account_id: Optional[int] = None
    ) -> dict:
        """Obtiene resumen mensual de transacciones."""
        # Base conditions
        base_conditions = and_(
            TransactionModel.user_id == user_id,
            func.extract("year", TransactionModel.transaction_date) == year,
            func.extract("month", TransactionModel.transaction_date) == month,
        )

        if account_id:
            base_conditions = and_(
                base_conditions, TransactionModel.account_id == account_id
            )

        # Total ingresos
        stmt_income = select(func.sum(TransactionModel.amount)).where(
            base_conditions, TransactionModel.type == TransactionType.INCOME
        )
        result_income = await self.db.execute(stmt_income)
        total_income = result_income.scalar() or 0

        # Total gastos
        stmt_expenses = select(func.sum(TransactionModel.amount)).where(
            base_conditions, TransactionModel.type == TransactionType.EXPENSE
        )
        result_expenses = await self.db.execute(stmt_expenses)
        total_expenses = result_expenses.scalar() or 0

        # Conteo de transacciones
        stmt_count = select(func.count(TransactionModel.id)).where(base_conditions)
        result_count = await self.db.execute(stmt_count)
        total_transactions = result_count.scalar()

        return {
            "year": year,
            "month": month,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_balance": float(total_income) - float(total_expenses),
            "total_transactions": total_transactions,
        }

    async def count_by_user(self, user_id: int) -> int:
        """Cuenta el total de transacciones de un usuario."""
        stmt = select(func.count(TransactionModel.id)).where(
            TransactionModel.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar()

    async def get_by_uuid_and_user_id(
        self, uuid: str, user_id: int
    ) -> Optional[Transaction]:
        """Obtiene transacción por UUID y user_id para validar ownership."""
        stmt = select(TransactionModel).where(
            and_(TransactionModel.uuid == uuid, TransactionModel.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def update_by_uuid(
        self, transaction_uuid: str, user_id: int, updates: dict
    ) -> Optional[Transaction]:
        """Actualiza transacción por UUID con validación de ownership."""
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.uuid == transaction_uuid,
                TransactionModel.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        # Aplicar actualizaciones solo a campos permitidos
        allowed_fields = [
            "description",
            "notes",
            "category_id",
            "transaction_type",
            "amount",
            "transaction_date",
        ]
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(model, field, value)

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_activity_by_account_id(self, account_id: int, limit: int = 5) -> List[Transaction, Optional[str]]:
        stmt = (
            select(TransactionModel, CategoryModel)
            .outerjoin(CategoryModel, TransactionModel.category_id == CategoryModel.id)
            .where(TransactionModel.account_id == account_id)
            .limit(limit)
            .order_by(TransactionModel.transaction_date.desc())
        )
        result = await self.db.execute(stmt)
        results = result.all()

        return [
            (self._model_to_entity(transaction_model), category_model.name if category_model else None)
            for transaction_model, category_model in results
        ]

