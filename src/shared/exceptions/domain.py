from shared.exceptions.base import ValidationError, NotFoundError, BusinessRuleError

# User Exceptions
class UserNotFoundError(NotFoundError):
    """Usuario no encontrado."""

    def __init__(self, user_id: int = None, email: str = None):
        if user_id:
            message = f"Usuario con ID {user_id} no encontrado"
        elif email:
            message = f"Usuario con email {email} no encontrado"
        else:
            message = "Usuario no encontrado"
        super().__init__(message, "USER_NOT_FOUND")


class UserInactiveError(BusinessRuleError):
    """Usuario inactivo."""

    def __init__(self):
        super().__init__("El usuario está inactivo", "USER_INACTIVE")


class EmailAlreadyExistsError(ValidationError):
    """Email ya existe."""

    def __init__(self, email: str):
        super().__init__(f"El email {email} ya está registrado", "EMAIL_EXISTS")


# Account Exceptions
class AccountNotFoundError(NotFoundError):
    """Cuenta no encontrada."""

    def __init__(self, account_id: int):
        super().__init__(f"Cuenta con ID {account_id} no encontrada", "ACCOUNT_NOT_FOUND")


class AccountInactiveError(BusinessRuleError):
    """Cuenta inactiva."""

    def __init__(self, account_id: int):
        super().__init__(f"La cuenta {account_id} está inactiva", "ACCOUNT_INACTIVE")


class InsufficientFundsError(BusinessRuleError):
    """Fondos insuficientes."""

    def __init__(self, account_id: int, required_amount: float, available_amount: float):
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

    def __init__(self, transaction_id: int):
        super().__init__(f"Transacción con ID {transaction_id} no encontrada", "TRANSACTION_NOT_FOUND")


class InvalidTransactionAmountError(ValidationError):
    """Monto de transacción inválido."""

    def __init__(self, amount: float):
        super().__init__(f"Monto de transacción inválido: {amount}", "INVALID_AMOUNT")


class CategoryNotFoundError(NotFoundError):
    """Categoría no encontrada."""

    def __init__(self, category_id: int):
        super().__init__(f"Categoría con ID {category_id} no encontrada", "CATEGORY_NOT_FOUND")


# Money Value Object Exceptions
class InvalidCurrencyError(ValidationError):
    """Moneda inválida."""

    def __init__(self, currency: str):
        super().__init__(f"Moneda inválida: {currency}", "INVALID_CURRENCY")


class CurrencyMismatchError(ValidationError):
    """Las monedas no coinciden."""

    def __init__(self, currency1: str, currency2: str):
        super().__init__(f"Las monedas no coinciden: {currency1} vs {currency2}", "CURRENCY_MISMATCH")


class NegativeAmountError(ValidationError):
    """Monto negativo no permitido."""

    def __init__(self, amount: float):
        super().__init__(f"Cantidad negativa no permitida: {amount}", "NEGATIVE_AMOUNT")
