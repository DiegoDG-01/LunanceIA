import uuid as uuid_lib
from dataclasses import dataclass, field
from datetime import UTC, datetime

from email_validator import EmailNotValidError, validate_email
from pydantic import EmailStr

from shared.exceptions.domain import InvalidEmailError


@dataclass
class User:
    name: str
    email: EmailStr | None = None
    password: str | None = None
    picture: str | None = None
    id: int | None = None  # ← Opcional, se asigna al guardar en DB
    uuid: str = field(default_factory=lambda: str(uuid_lib.uuid4()))  # ← Auto-genera
    email_verified: bool = False
    last_login: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )  # ← Auto-genera
    registration_date: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )  # ← Auto-genera
    is_active: bool = True
    # Cuentas de Google y Apple vinculadas (claim `sub` de su ID token).
    google_sub: str | None = None
    apple_sub: str | None = None

    @property
    def login_methods(self) -> list[str]:
        """Formas de entrar: `password`, `google` y/o `apple`. Nunca debería quedar vacía."""
        methods = []
        if self.password is not None:
            methods.append("password")
        if self.google_sub is not None:
            methods.append("google")
        if self.apple_sub is not None:
            methods.append("apple")
        return methods

    @classmethod
    def create_local_user(
        cls,
        name: str,
        password: str,
        email: str,
        email_verified: bool = False,
    ):
        """Usuario con correo y contraseña (el correo ya normalizado)."""
        return cls(
            name=name,
            password=password,
            email=email,
            email_verified=email_verified,
        )

    @classmethod
    def create_external_user(
        cls,
        name: str,
        email: str,
        *,
        google_sub: str | None = None,
        apple_sub: str | None = None,
    ):
        """Usuario creado al entrar con Google o Apple: el proveedor ya verificó el correo y
        no tiene contraseña (puede crear una con "Olvidé mi contraseña")."""
        return cls(
            name=name,
            email=email,
            password=None,
            email_verified=True,
            google_sub=google_sub,
            apple_sub=apple_sub,
        )

    def deactivate(self):
        self.is_active = False

    def activate(self):
        self.is_active = True

    def change_email(self, new_email: EmailStr) -> None:
        try:
            validate_email(str(new_email))
        except EmailNotValidError:
            raise InvalidEmailError(new_email)
        self.email = new_email
