from enum import Enum


class TransactionType(str, Enum):
    GASTO = "gasto"
    INGRESO = "ingreso"


class AccountType(str, Enum):
    EFECTIVO = "efectivo"
    DEBITO = "debito"
    CREDITO = "credito"
    AHORROS = "ahorros"
    INVERSION = "inversion"


class Frequency(str, Enum):
    DIARIA = "diaria"
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"
    BIMENSUAL = "bimensual"
    TRIMESTRAL = "trimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"


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