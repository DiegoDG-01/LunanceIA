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


class TransactionNotActivityError(BusinessRuleError):
    """No se encontro actividad en la cuenta."""

    def __init__(self):
        super().__init__("No se encontró actividad en la cuenta (Ingresos/Egresos)")


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


class InvestmentSettingsNotFoundError(NotFoundError):
    def __init__(self, investment_uuid: str):
        super().__init__(f"Investment con UUID {investment_uuid} no encontrada")


class CreditCardSettingsNotFoundError(NotFoundError):
    def __init__(self, credit_card_uuid: str):
        super().__init__(f"Credit Card Setting para {credit_card_uuid} no encontrada")


class InvalidAccountSettingsError(BusinessRuleError):
    def __init__(self, type_account: str):
        super().__init__(
            f"Los Settings para el tipo cuenta son invalidos ({type_account}) "
        )


class CurrencyMismatchError(ValidationError):
    """Las monedas no coinciden."""

    def __init__(self, currency1: str, currency2: str):
        super().__init__(f"Las monedas no coinciden: {currency1} vs {currency2}")


class NegativeAmountError(ValidationError):
    """Monto negativo no permitido."""

    def __init__(self, amount: float):
        super().__init__(f"Cantidad negativa no permitida: {amount}")


class AIProcessingError(LunanceException):
    """Error al procesar datos con el servicio de IA"""

    def __init__(self, message: str = "Error procesando datos con el servicio de IA"):
        super().__init__(message)


class AIInvalidResponseError(LunanceException):
    """Respuesta inválida del servicio de IA"""

    def __init__(
        self, message: str = "El servicio de IA devolvió una respuesta inválida"
    ):
        super().__init__(message)


class AIServiceError(LunanceException):
    """Error de comunicación con el servicio de IA"""

    def __init__(self, message: str = "Error comunicándose con el servicio de IA"):
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


class FinancialEngineNotAvailableError(LunanceException):
    """Raised when the Rust financial engine (fincore) is not installed."""

    def __init__(self):
        super().__init__("Financial engine module is not installed")


class UsernameAlreadyExistsError(ValidationError):
    def __init__(self):
        super().__init__("Username already exists")


class InvalidInvestmentRateError(ValidationError):
    def __init__(self, investment_rate: str):
        super().__init__(f"Investment Rate invalido: {investment_rate}")


class InvalidPenaltyPercentageError(ValidationError):
    def __init__(self, penalty_percentage: str):
        super().__init__(f"Penalty percentage invalido: {penalty_percentage}")


class InvalidInvestmentTypeError(ValidationError):
    def __init__(self, investment_type: str):
        super().__init__(f"Investment type invalido: {investment_type}")


class InvalidBillingCycleDayError(ValidationError):
    def __init__(self, billing_type: str):
        super().__init__(f"Billing type invalido: {billing_type}")


class InvalidPaymentDueDayError(ValidationError):
    def __init__(self, billing_type: str):
        super().__init__(f"Billing type invalido: {billing_type}")


class InvalidPaymentTypeError(ValidationError):
    def __init__(self, payment_type: str):
        super().__init__(f"Payment type invalido: {payment_type}")


class InvalidCreditLimitError(ValidationError):
    def __init__(self, credit_limit: str):
        super().__init__(f"Credit limit invalido: {credit_limit}")


class InvalidMinimumPaymentError(ValidationError):
    def __init__(self, minimum_payment: str):
        super().__init__(f"Minimum payment invalido: {minimum_payment}")


class InvalidEmailError(ValidationError):
    def __init__(self, email: str):
        super().__init__(f"Email invalido: {email}")


class InvalidBalanceUpdateError(BusinessRuleError):
    def __init__(self, valance_update: str):
        super().__init__(f"Valance update invalido: {valance_update}")

class InvalidInstallmentPaymentError(BusinessRuleError):
    def __init__(self, expected: str, received: str):
        super().__init__(f"Invalid account type: {expected} expected, {received} received")
