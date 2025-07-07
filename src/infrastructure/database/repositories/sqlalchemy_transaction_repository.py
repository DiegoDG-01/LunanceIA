from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from domain.entities.transaction import Transaction
from domain.repositories.transaction_repository import TransactionRepository
from domain.objects.money import Money
from domain.objects.enums import TransactionType
from infrastructure.database.models.transaction import TransactionModel


class SQLAlchemyTransactionRepository(TransactionRepository):
    """Implementación SQLAlchemy del repositorio de transacciones."""

    def __init__(self, db: Session):
        self.db = db

    def _model_to_entity(self, model: TransactionModel) -> Transaction:
        """Convierte modelo SQLAlchemy a entidad de dominio."""
        return Transaction(
            transaction_id=model.transaction_id,
            user_id=model.user_id,
            account_id=model.account_id,
            category_id=model.category_id,
            type=model.type,
            amount=Money(amount=model.amount, currency="MXN"),  # Asumo MXN por defecto
            transaction_date=model.transaction_date,
            description=model.description,
            notes=model.notes,
            creation_date=model.creation_date,
        )

    def _entity_to_model(self, entity: Transaction) -> TransactionModel:
        """Convierte entidad de dominio a modelo SQLAlchemy."""
        return TransactionModel(
            transaction_id=entity.transaction_id,
            user_id=entity.user_id,
            account_id=entity.account_id,
            category_id=entity.category_id,
            type=entity.type,
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
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Obtiene transacción por ID."""
        model = (
            self.db.query(TransactionModel)
            .filter(TransactionModel.transaction_id == transaction_id)
            .first()
        )

        return self._model_to_entity(model) if model else None

    async def get_by_id_and_user(
        self, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """Obtiene transacción que pertenezca al usuario especificado."""
        model = (
            self.db.query(TransactionModel)
            .filter(
                and_(
                    TransactionModel.transaction_id == transaction_id,
                    TransactionModel.user_id == user_id,
                )
            )
            .first()
        )

        return self._model_to_entity(model) if model else None

    async def get_by_user(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Obtiene todas las transacciones de un usuario con paginación."""
        models = (
            self.db.query(TransactionModel)
            .filter(TransactionModel.user_id == user_id)
            .order_by(desc(TransactionModel.creation_date))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [self._model_to_entity(model) for model in models]

    async def get_by_account(
        self, account_id: int, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Obtiene todas las transacciones de una cuenta específica."""
        models = (
            self.db.query(TransactionModel)
            .filter(
                and_(
                    TransactionModel.account_id == account_id,
                    TransactionModel.user_id == user_id,
                )
            )
            .order_by(desc(TransactionModel.creation_date))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [self._model_to_entity(model) for model in models]

    async def get_by_date_range(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        account_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
    ) -> List[Transaction]:
        """Obtiene transacciones en un rango de fechas."""
        query = self.db.query(TransactionModel).filter(
            and_(
                TransactionModel.user_id == user_id,
                TransactionModel.transaction_date >= start_date,
                TransactionModel.transaction_date <= end_date,
            )
        )

        if account_id:
            query = query.filter(TransactionModel.account_id == account_id)

        if transaction_type:
            query = query.filter(TransactionModel.type == transaction_type)

        models = query.order_by(desc(TransactionModel.transaction_date)).all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_category(
        self,
        user_id: int,
        category_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Transaction]:
        """Obtiene transacciones por categoría."""
        query = self.db.query(TransactionModel).filter(
            and_(
                TransactionModel.user_id == user_id,
                TransactionModel.category_id == category_id,
            )
        )

        if start_date:
            query = query.filter(TransactionModel.transaction_date >= start_date)

        if end_date:
            query = query.filter(TransactionModel.transaction_date <= end_date)

        models = query.order_by(desc(TransactionModel.transaction_date)).all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """Obtiene transacciones por tipo (ingreso/gasto)."""
        models = (
            self.db.query(TransactionModel)
            .filter(
                and_(
                    TransactionModel.user_id == user_id,
                    TransactionModel.type == transaction_type,
                )
            )
            .order_by(desc(TransactionModel.creation_date))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [self._model_to_entity(model) for model in models]

    async def update(self, transaction: Transaction) -> Transaction:
        """Actualiza una transacción."""
        model = (
            self.db.query(TransactionModel)
            .filter(TransactionModel.transaction_id == transaction.transaction_id)
            .first()
        )

        if not model:
            raise ValueError("Transacción no encontrada")

        # Actualizar campos
        model.category_id = transaction.category_id
        model.type = transaction.type
        model.amount = transaction.amount.amount
        model.transaction_date = transaction.transaction_date
        model.description = transaction.description
        model.notes = transaction.notes

        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, transaction_id: int, user_id: int) -> bool:
        """Elimina una transacción."""
        result = (
            self.db.query(TransactionModel)
            .filter(
                and_(
                    TransactionModel.transaction_id == transaction_id,
                    TransactionModel.user_id == user_id,
                )
            )
            .delete()
        )

        self.db.commit()
        return result > 0

    async def get_total_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_id: Optional[int] = None,
    ) -> float:
        """Obtiene el total de transacciones por tipo en un período."""
        query = self.db.query(func.sum(TransactionModel.amount)).filter(
            and_(
                TransactionModel.user_id == user_id,
                TransactionModel.type == transaction_type,
            )
        )

        if start_date:
            query = query.filter(TransactionModel.transaction_date >= start_date)

        if end_date:
            query = query.filter(TransactionModel.transaction_date <= end_date)

        if account_id:
            query = query.filter(TransactionModel.account_id == account_id)

        result = query.scalar()
        return float(result) if result else 0.0

    async def get_monthly_summary(
        self, user_id: int, year: int, month: int, account_id: Optional[int] = None
    ) -> dict:
        """Obtiene resumen mensual de transacciones."""
        # Filtro base
        query_base = self.db.query(TransactionModel).filter(
            and_(
                TransactionModel.user_id == user_id,
                func.extract("year", TransactionModel.transaction_date) == year,
                func.extract("month", TransactionModel.transaction_date) == month,
            )
        )

        if account_id:
            query_base = query_base.filter(TransactionModel.account_id == account_id)

        # Total ingresos
        total_income = (
            query_base.filter(TransactionModel.type == TransactionType.INCOME)
            .with_entities(func.sum(TransactionModel.amount))
            .scalar()
            or 0
        )

        # Total gastos
        total_expenses = (
            query_base.filter(TransactionModel.type == TransactionType.EXPENSE)
            .with_entities(func.sum(TransactionModel.amount))
            .scalar()
            or 0
        )

        # Conteo de transacciones
        total_transactions = query_base.count()

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
        return (
            self.db.query(TransactionModel)
            .filter(TransactionModel.user_id == user_id)
            .count()
        )
