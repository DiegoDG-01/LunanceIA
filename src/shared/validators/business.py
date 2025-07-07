"""Validadores de reglas de negocio."""

from decimal import Decimal
from datetime import date, timedelta

from shared.constants.business import (
    MAX_TRANSACTION_AMOUNT,
    MIN_TRANSACTION_AMOUNT,
    MAX_ACCOUNT_NAME_LENGTH,
    SUPPORTED_CURRENCIES,
)
from shared.exceptions.domain import (
    InvalidTransactionAmountError,
    InvalidCurrencyError,
    ValidationError,
)


class TransactionValidator:
    """Validador para transacciones."""

    @staticmethod
    def validate_amount(amount: Decimal) -> None:
        """Valida el monto de una transacción."""
        if amount <= 0:
            raise InvalidTransactionAmountError(float(amount))

        if amount < MIN_TRANSACTION_AMOUNT:
            raise ValidationError(f"El monto mínimo es {MIN_TRANSACTION_AMOUNT}")

        if amount > MAX_TRANSACTION_AMOUNT:
            raise ValidationError(f"El monto máximo es {MAX_TRANSACTION_AMOUNT}")

    @staticmethod
    def validate_date(transaction_date: date) -> None:
        """Valida la fecha de transacción."""
        today = date.today()

        # No permitir fechas muy futuras (más de una semana)
        max_future_date = today + timedelta(days=7)
        if transaction_date > max_future_date:
            raise ValidationError("No se permiten fechas futuras más de una semana")

        # No permitir fechas muy antiguas (más de 2 años)
        min_past_date = date(today.year - 2, 1, 1)
        if transaction_date < min_past_date:
            raise ValidationError(
                "La fecha es demasiado antigua para ser procesada, mas de 2 años de antiguedad"
            )


class AccountValidator:
    """Validador para cuentas."""

    @staticmethod
    def validate_name(name: str) -> None:
        """Valida el nombre de la cuenta."""
        if not name or not name.strip():
            raise ValidationError("El nombre de la cuenta es requerido")

        if len(name) > MAX_ACCOUNT_NAME_LENGTH:
            raise ValidationError(
                f"El nombre no puede exceder {MAX_ACCOUNT_NAME_LENGTH} caracteres"
            )

    @staticmethod
    def validate_currency(currency: str) -> None:
        """Valida el código de moneda."""
        if currency not in SUPPORTED_CURRENCIES:
            raise InvalidCurrencyError(currency)


class UserValidator:
    """Validador para usuarios."""

    @staticmethod
    def validate_email(email: str) -> None:
        """Valida el formato del email."""
        from shared.utils.validations import validate_email_format

        if not email or not email.strip():
            raise ValidationError("El email es requerido")

        if not validate_email_format(email):
            raise ValidationError("Formato de email inválido")

    @staticmethod
    def validate_password(password: str) -> None:
        """Valida la fortaleza de la contraseña."""
        from shared.utils.validations import validate_password_strength

        if not password:
            raise ValidationError("La contraseña es requerida")

        errors = validate_password_strength(password)
        if errors:
            raise ValidationError("; ".join(errors))
