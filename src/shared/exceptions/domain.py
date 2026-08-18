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


class InstallmentChargeNotFoundError(NotFoundError):
    """Cargo de compra a plazos no encontrado."""

    def __init__(self, charge_uuid: str):
        super().__init__(f"Cargo de compra a plazos con ID {charge_uuid} no encontrado")


class InstallmentChargeAlreadyPaidError(BusinessRuleError):
    """Cargo de compra a plazos ya pagado."""

    def __init__(self, charge_uuid: str):
        super().__init__(f"El cargo de compra a plazos {charge_uuid} ya fue pagado")


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


class InstallmentTransactionModificationError(BusinessRuleError):
    """Evita modificar movimientos que forman parte de una compra a meses."""

    def __init__(self):
        super().__init__(
            "La transacción inicial de una compra a meses no puede editarse ni eliminarse por separado"
        )


class CategoryNotFoundError(NotFoundError):
    """Categoría no encontrada."""

    def __init__(self, category_id: int):
        super().__init__(f"Categoría con ID {category_id} no encontrada")


# Money Value Object Exceptions
class InvalidCurrencyError(ValidationError):
    """Moneda inválida."""

    def __init__(self, currency: str):
        super().__init__(f"Moneda inválida: {currency}")


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
        super().__init__(
            f"Invalid account type: {expected} expected, {received} received"
        )


class BankNotFoundError(NotFoundError):
    """Banco no encontrado."""

    def __init__(self, bank_id: int | str):
        super().__init__(f"Banco con ID {bank_id} no encontrado")


class InstallmentPurchaseNotFoundError(NotFoundError):
    """Compra a plazos no encontrada."""

    def __init__(self, purchase_uuid: str):
        super().__init__(f"Compra a plazos con UUID {purchase_uuid} no encontrada")


class InvalidAIProviderError(ValidationError):
    """Proveedor de IA inválido."""

    def __init__(self, provider: str):
        super().__init__(f"Proveedor de IA inválido: {provider}")


class BulkDeleteFailedError(BusinessRuleError):
    """Eliminación masiva fallida."""

    def __init__(self, entity: str):
        super().__init__(f"No se pudieron eliminar los registros de {entity}")


class BudgetNotFoundError(NotFoundError):
    """Presupuesto no encontrado."""

    def __init__(self, budget_uuid: str):
        super().__init__(f"Presupuesto con UUID {budget_uuid} no encontrado")


class BudgetLimitExceededError(BusinessRuleError):
    """El gasto superó el límite del presupuesto."""

    def __init__(self, budget_name: str, limit: float, spent: float):
        super().__init__(
            f"El presupuesto '{budget_name}' ha superado su límite de {limit:.2f}. "
            f"Gasto actual: {spent:.2f}"
        )


class SavingGoalNotFoundError(NotFoundError):
    """Goal no encontrado."""

    def __init__(self, goal_uuid: str):
        super().__init__(f"Goal con UUID {goal_uuid} no encontrado")


class SameAccountTransferError(BusinessRuleError):
    """No se puede transferir a la misma cuenta."""

    def __init__(self):
        super().__init__("La cuenta origen y destino no pueden ser la misma")


class TransferNotAllowedError(BusinessRuleError):
    """Transferencia no permitida por regla de negocio."""

    def __init__(self, reason: str):
        super().__init__(f"Transferencia no permitida: {reason}")


class TransferAccountTypeNotAllowedError(BusinessRuleError):
    """Tipo de cuenta no permitida para transferencia."""

    def __init__(self, account_type: str):
        super().__init__(
            f"Tipo de cuenta no permitida para transferencia: {account_type}"
        )


class InvalidIncomeDateRangeError(ValidationError):
    """Rango de fechas de ingreso recurrente inválido."""

    def __init__(self, start_date: str, end_date: str):
        super().__init__(
            f"La fecha de fin ({end_date}) no puede ser anterior a la de inicio ({start_date})"
        )


class RecurringIncomeNotFoundError(NotFoundError):
    """Ingreso recurrente no encontrado."""

    def __init__(self, income_uuid: str):
        super().__init__(f"Ingreso recurrente con ID {income_uuid} no encontrado")


class IncomeDepositNotFoundError(NotFoundError):
    """Depósito de ingreso recurrente no encontrado."""

    def __init__(self, deposit_uuid: str):
        super().__init__(f"Depósito con ID {deposit_uuid} no encontrado")


class InvalidSubscriptionDateRangeError(ValidationError):
    """Rango de fechas de suscripción inválido."""

    def __init__(self, start_date: str, end_date: str):
        super().__init__(
            f"La fecha de fin ({end_date}) no puede ser anterior a la de inicio ({start_date})"
        )


# Investment Position Exceptions
class InvestmentPositionNotFoundError(NotFoundError):
    """Apartado de inversión no encontrado."""

    def __init__(self, position_uuid: str):
        super().__init__(f"Apartado de inversión con ID {position_uuid} no encontrado")


class InvestmentPositionNotActiveError(BusinessRuleError):
    """Apartado de inversión no activo."""

    def __init__(self, position_uuid: str, status: str):
        super().__init__(
            f"El apartado {position_uuid} no admite esta operación (estado: {status})"
        )


class InvestmentPositionLockedError(BusinessRuleError):
    """Apartado de inversión bloqueado por periodo de permanencia."""

    def __init__(self, position_uuid: str, lock_period_end_date: str):
        super().__init__(
            f"El apartado {position_uuid} está bloqueado hasta {lock_period_end_date}"
        )


class FixedTermDepositNotAllowedError(BusinessRuleError):
    """Depósito no permitido en apartado a plazo fijo."""

    def __init__(self, position_uuid: str):
        super().__init__(
            f"El apartado {position_uuid} es a plazo fijo y no admite depósitos después de creado"
        )


class FixedTermWithdrawalNotAllowedError(BusinessRuleError):
    """Retiro parcial no permitido en apartado a plazo fijo."""

    def __init__(self, position_uuid: str):
        super().__init__(
            f"El apartado {position_uuid} es a plazo fijo y no admite retiros parciales; debe liquidarse por completo"
        )


class InvalidFixedTermConfigError(ValidationError):
    """Configuración de plazo fijo inválida."""

    def __init__(self):
        super().__init__(
            "Un apartado a plazo fijo requiere 'term_days' o 'maturity_date'"
        )


class InvestmentPositionNotMaturedError(BusinessRuleError):
    """Apartado de inversión aún no vencido."""

    def __init__(self, position_uuid: str, maturity_date: str):
        super().__init__(
            f"El apartado {position_uuid} aún no vence (vencimiento: {maturity_date})"
        )


class PositionAccountTypeNotAllowedError(BusinessRuleError):
    """Tipo de cuenta no admite apartados de inversión."""

    def __init__(self, account_type: str):
        super().__init__(
            f"Las cuentas de tipo {account_type} no admiten apartados de inversión"
        )


class InvalidPositionCapError(ValidationError):
    """Configuración de tope y desbordamiento inválida."""

    def __init__(self, reason: str):
        super().__init__(f"Configuración de tope inválida: {reason}")


class PositionCapExceededError(BusinessRuleError):
    """El monto inicial del apartado supera su propio tope."""

    def __init__(self, amount: str, max_balance: str):
        super().__init__(
            f"El monto {amount} supera el tope {max_balance} del apartado; "
            f"crea el apartado dentro del tope y deposita el resto después"
        )


class InvalidOverflowTargetError(BusinessRuleError):
    """Destino de desbordamiento inválido."""

    def __init__(self, reason: str):
        super().__init__(f"Destino de desbordamiento inválido: {reason}")


class FixedTermCapNotAllowedError(BusinessRuleError):
    """Tope y desbordamiento no aplican a apartados a plazo fijo."""

    def __init__(self):
        super().__init__(
            "Un apartado a plazo fijo no admite tope ni desbordamiento: "
            "su monto queda fijo hasta el vencimiento"
        )
