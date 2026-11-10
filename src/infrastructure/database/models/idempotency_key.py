from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CHAR, JSON, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base


class IdempotencyKeyModel(Base):
    """Una `Idempotency-Key` por usuario y operación (ver `IdempotencyService`).

    Debe coincidir con la migración `d5e2b8c4a917`.
    """

    __tablename__ = "idempotency_keys"

    # La clave es única por usuario: dos cuentas pueden mandar el mismo UUID sin pisarse.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(CHAR(36), primary_key=True)
    # SHA-256 en hex de método + ruta + cuerpo.
    request_hash: Mapped[str] = mapped_column(CHAR(64))
    # NULL mientras la respuesta no se ha guardado.
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # none_as_null: una respuesta sin cuerpo (204) se guarda como NULL, no como 'null'.
    response: Mapped[Any | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (Index("ix_idempotency_keys_created_at", "created_at"),)
