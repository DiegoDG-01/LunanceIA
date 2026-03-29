from enum import Enum


class InterestType(str, Enum):
    SIMPLE = "SIMPLE"
    COMPOUND = "COMPOUND"


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
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    BIMONTHLY = "BIMONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    ANNUAL = "ANNUAL"


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


class CategoryName(str, Enum):
    COMIDA = "Comida"
    TRANSPORTE = "Transporte"
    SUELDO = "Sueldo"
    INVERSIONES = "Inversiones"
    VIAJES = "Viajes"
    VIVIENDA = "Vivienda"
    SERVICIOS = "Servicios"
    SALUD = "Salud"
    ENTRETENIMIENTO = "Entretenimiento"
    COMPRAS = "Compras"
    EDUCACION = "Educación"
    SUSCRIPCIONES = "Suscripciones"
    REGALOS = "Regalos"
    IMPUESTOS = "Impuestos"
    OTROS_GASTOS = "Otros Gastos"
    VENTAS = "Ventas"
    PREMIOS = "Premios"
    OTROS_INGRESOS = "Otros Ingresos"
