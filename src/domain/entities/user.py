from dataclasses import dataclass
from datetime import datetime
from email_validator import validate_email, EmailNotValidError

import uuid


@dataclass
class User:
    uuid: str
    name: str
    email: str
    password_hash: str
    registration_date: datetime
    is_active: bool = True

    @classmethod
    def create_new(cls, name: str, email: str, password_hash: str):
        """Factory method to create a new user"""
        return cls(
            uuid=str(uuid.uuid4()),
            name=name,
            email=email,
            password_hash=password_hash,
            registration_date=datetime.now(),
            is_active=True,
        )

    def deactivate(self):
        self.is_active = False

    def activate(self):
        self.is_active = True

    def change_email(self, new_email: str) -> None:
        try:
            validate_email(new_email)
        except EmailNotValidError:
            raise ValueError("Email is not valid")
        self.email = new_email
