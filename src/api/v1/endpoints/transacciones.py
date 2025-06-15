from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Transaction, User, Account, Tag
from schemas import (
    CreateTransaction,
    UpdateTransaction,
    TransactionDetails
)

from utils.enums import TransactionType
from api.deps import get_current_active_user

router = APIRouter()


@router.post("/", response_model=TransactionDetails)
def create_transaction(
        transaction_in: CreateTransaction,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Crear una nueva transacción"""
    # Verificar que la cuenta pertenece al usuario
    cuenta = db.query(Account).filter(
        Account.account_id == transaction_in.account_id,
        Account.user_id == current_user.user_id
    ).first()

    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    # Crear transacción
    db_transaccion = Transaction(
        **transaction_in.dict(exclude={"etiquetas_ids"}),
        user_id=current_user.user_id
    )

    # Agregar etiquetas si se proporcionaron
    if transaction_in.etiquetas_ids:
        etiquetas = db.query(Tag).filter(
            Tag.tag_id.in_(transaction_in.etiquetas_ids),
            Tag.user_id == current_user.user_id
        ).all()
        db_transaccion.etiquetas = etiquetas

    db.add(db_transaccion)

    # Actualizar saldo de la cuenta
    if transaction_in.tipo == TransactionType.INGRESO:
        Account.current_balance += transaction_in.monto
    else:
        Account.current_balance -= transaction_in.monto

    db.commit()
    db.refresh(db_transaccion)

    return db_transaccion


@router.get("/", response_model=List[TransactionDetails])
def read_transacciones(
        skip: int = 0,
        limit: int = 100,
        fecha_inicio: Optional[date] = Query(None),
        fecha_fin: Optional[date] = Query(None),
        tipo: Optional[TransactionType] = Query(None),
        id_categoria: Optional[int] = Query(None),
        id_cuenta: Optional[int] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Obtener transacciones del usuario con filtros opcionales"""
    query = db.query(Transaction).filter(
        Transaction.user_id == current_user.user_id,
    ).options(
        joinedload(Transaction.category),
        joinedload(Transaction.account),
        joinedload(Transaction.tags)
    )

    if fecha_inicio:
        query = query.filter(Transaction.creation_date >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Transaction.transaction_date <= fecha_fin)
    if tipo:
        query = query.filter(Transaction.type == tipo)
    if id_categoria:
        query = query.filter(Transaction.category_id == id_categoria)
    if id_cuenta:
        query = query.filter(Transaction.account_id == id_cuenta)

    transacciones = query.order_by(Transaction.creation_date.desc()).offset(skip).limit(limit).all()
    return transacciones


@router.get("/{id_transaccion}", response_model=TransactionDetails)
def read_transaction(
        id_transaccion: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Obtener una transacción específica"""
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == id_transaccion,
        Transaction.user_id == current_user.user_id
    ).options(
        joinedload(Transaction.category),
        joinedload(Transaction.account),
        joinedload(Transaction.tags)
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    return transaction


@router.put("/{id_transaction}", response_model=TransactionDetails)
def update_transaction(
        transaction_id: int,
        transaction_in: UpdateTransaction,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Actualizar una transacción"""
    transaction = db.query(Transaction).filter(
        Transaction.transaction_id == transaction_id,
        Transaction.user_id == current_user.user_id,
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    # Revertir el efecto en el saldo de la cuenta anterior
    cuenta_anterior = transaction.account
    if transaction.type == TransactionType.INGRESO:
        cuenta_anterior.saldo_actual -= transaction.amount
    else:
        cuenta_anterior.saldo_actual += transaction.amount

    # Actualizar campos
    update_data = transaction_in.dict(exclude_unset=True, exclude={"etiquetas_ids"})
    for field, value in update_data.items():
        setattr(transaction, field, value)

    # Actualizar etiquetas si se proporcionaron
    if transaction_in.etiquetas_ids is not None:
        etiquetas = db.query(Tag).filter(
            Tag.tag_id.in_(transaction_in.etiquetas_ids),
            Tag.user_id == current_user.user_id
        ).all()
        transaction.etiquetas = etiquetas

    # Aplicar el nuevo efecto en el saldo
    cuenta_nueva = transaction.account
    if transaction.type == TransactionType.INGRESO:
        cuenta_nueva.saldo_actual += transaction.amount
    else:
        cuenta_nueva.saldo_actual -= transaction.amount

    db.commit()
    db.refresh(transaction)

    return transaction


@router.delete("/{id_transaccion}")
def delete_transaccion(
        id_transaccion: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Eliminar una transacción"""
    transaccion = db.query(Transaction).filter(
        Transaction.transaction_id == id_transaccion,
        Transaction.user_id == current_user.user_id
    ).first()

    if not transaccion:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    # Revertir el efecto en el saldo de la cuenta
    cuenta = transaccion.account
    if transaccion.type == TransactionType.INGRESO:
        cuenta.saldo_actual -= transaccion.amount
    else:
        cuenta.saldo_actual += transaccion.amount

    db.delete(transaccion)
    db.commit()

    return {"detail": "Transacción eliminada exitosamente"}
