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
        super().__init__("El usuario está inactivo")


class EmailAlreadyExistsError(ValidationError):
    """Email ya existe."""

    def __init__(self, email: EmailStr):
        super().__init__(f"El email {email} ya está registrado")


# Account Exceptions
class AccountNotFoundError(NotFoundError):
    """Cuenta no encontrada."""

    def __init__(self, account_uuid: str):
        super().__init__(f"Cuenta con ID {account_uuid} no encontrada")


class SubscriptionNotFoundError(NotFoundError):
    """Suscripción no encontrada."""

    def __init__(self, subscription_uuid: str):
        super().__init__(f"Suscripción con ID {subscription_uuid} no encontrada")


class AccountInactiveError(BusinessRuleError):
    """Cuenta inactiva."""

    def __init__(self, account_id: int):
        super().__init__(f"La cuenta {account_id} está inactiva")


class InsufficientFundsError(BusinessRuleError):
    """Fondos insuficientes."""

    def __init__(self, required_amount: float, available_amount: float):
        self.required_amount = required_amount
        self.available_amount = available_amount
        message = f"Fondos insuficientes en cuenta. Requerido: {required_amount}, Disponible: {available_amount}"
        super().__init__(message)


class AccountHasBalanceError(BusinessRuleError):
    """No se puede eliminar cuenta con balance."""

    def __init__(self, account_id: int, balance: float):
        message = f"No se puede eliminar la cuenta {account_id} con balance {balance}"
        super().__init__(message)


class AccountHasTransactionsError(BusinessRuleError):
    """No se puede eliminar cuenta con transacciones."""

    def __init__(self, account_id: int):
        message = f"No se puede eliminar la cuenta {account_id} porque tiene transacciones asociadas"
        super().__init__(message)


# Transaction Exceptions
class TransactionNotFoundError(NotFoundError):
    """Transacción no encontrada."""

    def __init__(self, transaction_uuid: str):
        super().__init__(f"Transacción con UUID {transaction_uuid} no encontrada")


class InvalidTransactionAmountError(ValidationError):
    """Monto de transacción inválido."""

    def __init__(self, amount: float):
        super().__init__(f"Monto de transacción inválido: {amount}")


class InvalidTransactionTypeError(ValidationError):
    """Tipo de transacción inválido."""

    def __init__(self, transaction_type: str):
        super().__init__(f"Tipo de transacción inválido: {transaction_type}")


class CategoryNotFoundError(NotFoundError):
    """Categoría no encontrada."""

    def __init__(self, category_id: int):
        super().__init__(f"Categoría con ID {category_id} no encontrada")


# Money Value Object Exceptions
class InvalidCurrencyError(ValidationError):
    """Moneda inválida."""

    def __init__(self, currency: str):
        super().__init__(f"Moneda inválida: {currency}")


class CurrencyMismatchError(ValidationError):
    """Las monedas no coinciden."""

    def __init__(self, currency1: str, currency2: str):
        super().__init__(f"Las monedas no coinciden: {currency1} vs {currency2}")


class NegativeAmountError(ValidationError):
    """Monto negativo no permitido."""

    def __init__(self, amount: float):
        super().__init__(f"Cantidad negativa no permitida: {amount}")


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
