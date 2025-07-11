"""Constantes de reglas de negocio."""

from decimal import Decimal

# Límites monetarios
MAX_TRANSACTION_AMOUNT = Decimal("1000000.00")  # 1 millón
MIN_TRANSACTION_AMOUNT = Decimal("0.01")  # 1 centavo
MAX_ACCOUNT_BALANCE = Decimal("10000000.00")  # 10 millones

# Límites de texto
MAX_ACCOUNT_NAME_LENGTH = 100
MAX_TRANSACTION_DESCRIPTION_LENGTH = 500
MAX_TRANSACTION_NOTES_LENGTH = 1000
MAX_USER_NAME_LENGTH = 100

# Configuración de paginación
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Períodos de tiempo
TRANSACTION_HISTORY_DAYS = 365  # 1 año
MAX_EXPORT_TRANSACTIONS = 10000

# Monedas soportadas
SUPPORTED_CURRENCIES = ["MXN", "USD", "EUR", "GBP"]
DEFAULT_CURRENCY = "MXN"

# Categorías por defecto (IDs)
DEFAULT_INCOME_CATEGORY = 1
DEFAULT_EXPENSE_CATEGORY = 2

# Configuración de reportes
MAX_REPORT_MONTHS = 24  # 2 años
DEFAULT_REPORT_MONTHS = 12  # 1 año
