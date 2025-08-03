from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import Optional, List, Tuple

from domain.entities.transaction import Transaction
from domain.repositories.transaction_repository import TransactionRepository
from domain.objects.money import Money
from domain.objects.enums import TransactionType, AccountType
from infrastructure.database.models.transaction import TransactionModel
from infrastructure.database.models.account import AccountModel


class SQLAlchemyTransactionRepository(TransactionRepository):
    """Implementación SQLAlchemy del repositorio de transacciones."""

    def __init__(self, db: Session):
        self.db = db

    def _models_to_entity_with_account(
        self, transaction_model: TransactionModel, account_model: AccountModel
    ) -> tuple[Transaction, str, AccountType, Optional[str]]:
        transaction = self._model_to_entity(transaction_model)
        return transaction, account_model.name, account_model.type, account_model.bank

    def _model_to_entity(self, model: TransactionModel) -> Transaction:
        """Convierte modelo SQLAlchemy a entidad de dominio."""
        return Transaction(
            id=model.id,
            uuid=model.uuid,
            user_id=model.user_id,
            account_id=model.account_id,
            category_id=model.category_id,
            transaction_type=model.type,
            amount=Money(amount=model.amount, currency="MXN"),  # Asumo MXN por defecto
            transaction_date=model.transaction_date,
            description=model.description,
            notes=model.notes,
            creation_date=model.creation_date,
        )

    def _entity_to_model(self, entity: Transaction) -> TransactionModel:
        """Convierte entidad de dominio a modelo SQLAlchemy."""
        return TransactionModel(
            id=None,
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

    def create(self, transaction: Transaction) -> Transaction:
        """Crea una nueva transacción."""
        model = self._entity_to_model(transaction)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Obtiene transacción por ID."""
        model = (
            self.db.query(TransactionModel)
            .filter(TransactionModel.id == transaction_id)
            .first()
        )

        return self._model_to_entity(model) if model else None

    def get_by_id_and_user_uuid(
        self, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """Obtiene transacción por ID y UUID del usuario."""
        model = (
            self.db.query(TransactionModel)
            .filter(
                and_(
                    TransactionModel.id == transaction_id,
                    TransactionModel.user_id == user_id,
                )
            )
            .first()
        )

        return self._model_to_entity(model) if model else None

    def get_by_id_and_user(
        self, transaction_id: int, user_id: int
    ) -> Optional[Transaction]:
        """Obtiene transacción que pertenezca al usuario especificado."""
        model = (
            self.db.query(TransactionModel)
            .filter(
                and_(
                    TransactionModel.id == transaction_id,
                    TransactionModel.user_id == user_id,
                )
            )
            .first()
        )

        return self._model_to_entity(model) if model else None

    def get_by_user(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Transaction]:
        """Obtiene todas las transacciones de un usuario con paginación."""
        results = (
            self.db.query(TransactionModel, AccountModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .filter(TransactionModel.user_id == user_id)
            .order_by(desc(TransactionModel.creation_date))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [
            self._models_to_entity_with_account(transaction, acc)
            for transaction, acc in results
        ]

    def get_by_account(
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

    def get_by_date_range(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_uuid: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
    ) -> List[Transaction]:
        """Obtiene transacciones en un rango de fechas."""
        query = (
            self.db.query(TransactionModel, AccountModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .filter(TransactionModel.user_id == user_id)
        )

        if start_date:
            query = query.filter(TransactionModel.transaction_date >= start_date)

        if end_date:
            query = query.filter(TransactionModel.transaction_date <= end_date)

        if account_uuid:
            query = query.filter(AccountModel.uuid == account_uuid)

        if transaction_type:
            query = query.filter(TransactionModel.type == transaction_type)

        results = query.order_by(desc(TransactionModel.transaction_date)).all()

        return [
            self._models_to_entity_with_account(transaction, acc)
            for transaction, acc in results
        ]

    def get_by_category(
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

    def get_by_uuid_with_account_details(
        self, uuid: str, user_id: int
    ) -> Optional[Tuple[Transaction, str, AccountType, Optional[str]]]:
        result = (
            self.db.query(TransactionModel, AccountModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .filter(
                and_(TransactionModel.uuid == uuid, TransactionModel.user_id == user_id)
            )
            .first()
        )

        if not result:
            return None

        transaction_model, account_model = result
        return self._models_to_entity_with_account(transaction_model, account_model)

    def get_by_type(
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

    def update(self, transaction: Transaction) -> Transaction:
        """Actualiza una transacción."""
        model = (
            self.db.query(TransactionModel)
            .filter(TransactionModel.uuid == transaction.uuid)
            .first()
        )

        if not model:
            raise ValueError("Transacción no encontrada")

        # Actualizar campos
        if transaction.category_id is not None:
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

        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    def delete_by_uuid(self, uuid: str, user_id: int) -> bool:
        """Elimina una transacción."""
        result = (
            self.db.query(TransactionModel)
            .filter(
                and_(
                    TransactionModel.uuid == uuid,
                    TransactionModel.user_id == user_id,
                )
            )
            .delete(synchronize_session=False)
        )

        self.db.commit()
        return result > 0

    def get_total_by_type(
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

    def get_monthly_summary(
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

    def count_by_user(self, user_id: int) -> int:
        """Cuenta el total de transacciones de un usuario."""
        return (
            self.db.query(TransactionModel)
            .filter(TransactionModel.user_id == user_id)
            .count()
        )

    def get_by_uuid_and_user_id(self, uuid: str, user_id: int) -> Optional[Transaction]:
        """Obtiene transacción por UUID y user_id para validar ownership."""
        model = (
            self.db.query(TransactionModel)
            .filter(
                and_(TransactionModel.uuid == uuid, TransactionModel.user_id == user_id)
            )
            .first()
        )
        return self._model_to_entity(model) if model else None

    def update_by_uuid(
        self, transaction_uuid: str, user_id: int, updates: dict
    ) -> Optional[Transaction]:
        """Actualiza transacción por UUID con validación de ownership."""
        model = (
            self.db.query(TransactionModel)
            .filter(
                and_(
                    TransactionModel.uuid == transaction_uuid,
                    TransactionModel.user_id == user_id,
                )
            )
            .first()
        )

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

        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)
