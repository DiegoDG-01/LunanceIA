from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import User
from schemas import (
    User as UserSchema,
    CreateUser,
    UpdateUser,
    UserWithStats
)
from core.security import get_password_hash
from api.deps import get_current_active_user

router = APIRouter()


@router.post("/register", response_model=UserSchema)
def register(
        *,
        db: Session = Depends(get_db),
        user_in: CreateUser,
) -> Any:
    """
    Crear nuevo User (registro público)
    """
    # Verificar si el email ya existe
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )

    # Crear nuevo User
    db_user = User(
        name=user_in.name,
        email=str(user_in.email),
        password_hash=get_password_hash(user_in.password),
        is_active=user_in.is_active,
    )

    db.add(db_user)

    try:
        db.commit()
        db.refresh(db_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al crear el User"
        )

    return db_user


@router.get("/me", response_model=UserWithStats)
def read_user_me(
        current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Obtener información del User actual con estadísticas
    """
    # Calcular estadísticas
    total_accounts = len(current_user.accounts)
    total_transactions = len(current_user.transactions)
    total_suscripciones_activas = len([s for s in current_user.subscriptions if s.activa])

    user_dict = {
        **current_user.__dict__,
        "total_accounts": total_accounts,
        "total_transacciones": total_transactions,
        "total_suscripciones_activas": total_suscripciones_activas
    }

    return UserWithStats(**user_dict)


@router.put("/me", response_model=UserSchema)
def update_user_me(
        *,
        db: Session = Depends(get_db),
        user_in: UpdateUser,
        current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Actualizar User actual
    """
    # Verificar si se está actualizando el email
    if user_in.email and user_in.email != current_user.email:
        existing_user = db.query(User).filter(User.email == user_in.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está en uso"
            )

    # Actualizar campos
    update_data = user_in.model_dump(exclude_unset=True)

    # Sí se actualiza la contraseña, cifrarla
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["password_hash"] = hashed_password

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user


@router.delete("/me")
def delete_user_me(
        *,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Eliminar User actual (soft delete)
    """
    current_user.activo = False
    db.add(current_user)
    db.commit()

    return {"detail": "User desactivado exitosamente"}


# Endpoints administrativos (opcional)
@router.get("/", response_model=List[UserSchema])
def read_users(
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> Any:
    """
    Obtener lista de Users (solo para testing, agregar verificación de admin en producción)
    """
    # TODO: Verificar que current_user sea admin
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserSchema)
def read_user_by_id(
        user_id: int,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
) -> Any:
    """
    Obtener User por ID (solo puede ver su propia información)
    """
    if current_user.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta información"
        )

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User no encontrado"
        )

    return user