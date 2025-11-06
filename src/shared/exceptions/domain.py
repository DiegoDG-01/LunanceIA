from pydantic import EmailStr
from shared.exceptions.base import (
    ValidationError,
    NotFoundError,
    BusinessRuleError,
    LunanceException,
)


# User Exceptions
class UserNotFoundError(NotFoundError):
    """Usuario no encontrado."""

    def __init__(self):
        super().__init__("User not found")


class InvalidCredentialsError(BusinessRuleError):
    """Credenciales inválidas."""

    def __init__(self, type):
        super().__init__(f"Invalid credentials for {type}")


class UserInactiveError(BusinessRuleError):
    """Usuario inactivo."""

    def __init__(self):
        super().__init__("El usuario está inactivo", "USER_INACTIVE")


class EmailAlreadyExistsError(ValidationError):
    """Email ya existe."""

    def __init__(self, email: EmailStr):
        super().__init__(f"El email {email} ya está registrado")


# Account Exceptions
class AccountNotFoundError(NotFoundError):
    """Cuenta no encontrada."""

    def __init__(self, account_uuid: str):
        super().__init__(
            f"Cuenta con ID {account_uuid} no encontrada", "ACCOUNT_NOT_FOUND"
        )


class AccountInactiveError(BusinessRuleError):
    """Cuenta inactiva."""

    def __init__(self, account_id: int):
        super().__init__(f"La cuenta {account_id} está inactiva", "ACCOUNT_INACTIVE")


class InsufficientFundsError(BusinessRuleError):
    """Fondos insuficientes."""

    def __init__(
        self, account_id: int, required_amount: float, available_amount: float
    ):
        message = f"Fondos insuficientes en cuenta {account_id}. Requerido: {required_amount}, Disponible: {available_amount}"
        super().__init__(message, "INSUFFICIENT_FUNDS")


class AccountHasBalanceError(BusinessRuleError):
    """No se puede eliminar cuenta con balance."""

    def __init__(self, account_id: int, balance: float):
        message = f"No se puede eliminar la cuenta {account_id} con balance {balance}"
        super().__init__(message, "ACCOUNT_HAS_BALANCE")


class AccountHasTransactionsError(BusinessRuleError):
    """No se puede eliminar cuenta con transacciones."""

    def __init__(self, account_id: int):
        message = f"No se puede eliminar la cuenta {account_id} porque tiene transacciones asociadas"
        super().__init__(message, "ACCOUNT_HAS_TRANSACTIONS")


# Transaction Exceptions
class TransactionNotFoundError(NotFoundError):
    """Transacción no encontrada."""

    def __init__(self, transaction_uuid: str):
        super().__init__(
            f"Transacción con UUID {transaction_uuid} no encontrada",
            "TRANSACTION_NOT_FOUND",
        )


class InvalidTransactionAmountError(ValidationError):
    """Monto de transacción inválido."""

    def __init__(self, amount: float):
        super().__init__(f"Monto de transacción inválido: {amount}", "INVALID_AMOUNT")


class InvalidTransactionTypeError(ValidationError):
    """Tipo de transacción inválido."""

    def __init__(self, transaction_type: str):
        super().__init__(
            f"Tipo de transacción inválido: {transaction_type}",
            "INVALID_TRANSACTION_TYPE",
        )


class CategoryNotFoundError(NotFoundError):
    """Categoría no encontrada."""

    def __init__(self, category_id: int):
        super().__init__(
            f"Categoría con ID {category_id} no encontrada", "CATEGORY_NOT_FOUND"
        )


# Money Value Object Exceptions
class InvalidCurrencyError(ValidationError):
    """Moneda inválida."""

    def __init__(self, currency: str):
        super().__init__(f"Moneda inválida: {currency}", "INVALID_CURRENCY")


class CurrencyMismatchError(ValidationError):
    """Las monedas no coinciden."""

    def __init__(self, currency1: str, currency2: str):
        super().__init__(
            f"Las monedas no coinciden: {currency1} vs {currency2}", "CURRENCY_MISMATCH"
        )


class NegativeAmountError(ValidationError):
    """Monto negativo no permitido."""

    def __init__(self, amount: float):
        """
        Initialize the exception for a negative amount value.

        Parameters:
            amount (float): The negative amount that triggered the exception.
        """
        super().__init__(f"Cantidad negativa no permitida: {amount}", "NEGATIVE_AMOUNT")


class GeminiProcessingError(LunanceException):
    """Error al procesar imagen con Gemini"""

    def __init__(self, message: str = "Error procesando imagen con Gemini"):
        """
        Initialize a GeminiProcessingError with an optional custom error message.
        """
        super().__init__(message)


class GeminiInvalidResponseError(LunanceException):
    """Respuesta inválida de Gemini"""

    def __init__(self, message: str = "Gemini devolvió una respuesta inválida"):
        """
        Initialize a GeminiInvalidResponseError with an optional custom message.

        Parameters:
            message (str): Custom error message describing the invalid response from Gemini. Defaults to "Gemini devolvió una respuesta inválida".
        """
        super().__init__(message)


class GeminiAPIError(LunanceException):
    """Error de comunicación con Gemini API"""

    def __init__(self, message: str = "Error comunicándose con Gemini API"):
        """
        Initialize a GeminiAPIError with an optional custom error message.

        Parameters:
            message (str): Custom error message describing the API communication error. Defaults to "Error comunicándose con Gemini API".
        """
        super().__init__(message)


class InvalidImageError(LunanceException):
    """Imagen inválida o no procesable"""

    def __init__(self, message: str = "La imagen proporcionada no es válida"):
        """
        Initialize the exception for invalid or unprocessable images.

        Parameters:
            message (str): Optional custom error message describing the image validation failure.
        """
        super().__init__(message)
