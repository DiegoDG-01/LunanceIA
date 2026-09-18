import uuid as uuid_lib
from dataclasses import dataclass, field
from datetime import UTC, datetime

from email_validator import EmailNotValidError, validate_email
from pydantic import EmailStr

from shared.exceptions.domain import InvalidEmailError


@dataclass
class User:
    name: str
    auth0_id: str | None = None
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

    @classmethod
    def create_auth0_user(
        cls,
        auth0_id: str,
        name: str,
        email: str,
        picture: str,
        email_verified: bool,
    ):
        """Factory method to create a new user"""
        return cls(
            auth0_id=auth0_id,
            name=name,
            email=email,
            picture=picture,
            email_verified=email_verified,
        )

    @classmethod
    def create_local_user(
        cls,
        name: str,
        password: str,
    ):
        """Factory method to create a new user"""
        return cls(
            name=name,
            password=password,
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
