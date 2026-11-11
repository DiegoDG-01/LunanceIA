import uuid
from datetime import datetime

from sqlalchemy import CHAR, DateTime, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from infrastructure.database.connection import Base

_SUBJECT = String(255).with_variant(
    mysql.VARCHAR(255, charset="utf8mb4", collation="utf8mb4_bin"), "mysql"
)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    # Identificador de login: obligatorio, único y normalizado (sin espacios, minúsculas).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # NULL en las cuentas creadas con Google o Apple que aún no eligieron contraseña.
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    picture: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_verified: Mapped[bool] = mapped_column(default=False)
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    registration_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # `sub` de Google y de Apple: identifican la cuenta del proveedor para siempre (el correo
    # puede cambiar). Distinguen mayúsculas, así que en MySQL van con collation binaria.
    google_sub: Mapped[str | None] = mapped_column(
        _SUBJECT, unique=True, index=True, nullable=True
    )
    apple_sub: Mapped[str | None] = mapped_column(
        _SUBJECT, unique=True, index=True, nullable=True
    )
    # Refresh token de Apple cifrado (AES-GCM): solo sirve para revocar la autorización
    # cuando se borre la cuenta. Nunca se guarda en claro.
    apple_refresh_token: Mapped[str | None] = mapped_column(String(1024), nullable=True)
