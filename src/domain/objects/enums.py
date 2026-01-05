from enum import Enum


class TransactionType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class AccountType(str, Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    INVESTMENT = "INVESTMENT"
    CASH = "CASH"


class Frequency(str, Enum):
    DAILY = "diaria"
    WEEKLY = "semanal"
    BIWEEKLY = "quincenal"
    MONTHLY = "mensual"
    BIMONTHLY = "bimensual"
    QUARTERLY = "trimestral"
    SEMI_ANNUAL = "semestral"
    ANNUAL = "anual"


class TransactionStatus(str, Enum):
    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    FALLIDO = "fallido"
    CANCELADO = "cancelado"


class BudgetPeriod(str, Enum):
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"
    TRIMESTRAL = "trimestral"
    ANUAL = "anual"


class ReminderType(str, Enum):
    PAGO = "pago"
    COBRO = "cobro"
    REVISION = "revision"
    OTRO = "otro"
