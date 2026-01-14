"""
⚠️ DEPRECADO: Este archivo está deprecado.
Usar shared/constants/validation_messages.py en su lugar.

Mantenido solo por compatibilidad hacia atrás.
"""

import warnings

warnings.warn(
    "error_messages.py está deprecado. Usar validation_messages.py",
    DeprecationWarning,
    stacklevel=2
)

"""Mensajes de error estandarizados."""

# Errores de autenticación
AUTH_INVALID_CREDENTIALS = "Credenciales inválidas"
AUTH_TOKEN_EXPIRED = "Token expirado"
AUTH_TOKEN_INVALID = "Token inválido"
AUTH_USER_INACTIVE = "Usuario inactivo"
AUTH_ACCESS_DENIED = "Acceso denegado"

# Errores de validación
VALIDATION_REQUIRED_FIELD = "Este campo es requerido"
VALIDATION_INVALID_EMAIL = "Formato de email inválido"
VALIDATION_INVALID_AMOUNT = "Monto inválido"
VALIDATION_AMOUNT_TOO_HIGH = "El monto excede el límite máximo"
VALIDATION_AMOUNT_TOO_LOW = "El monto es menor al mínimo permitido"
VALIDATION_INVALID_DATE = "Fecha inválida"
VALIDATION_FUTURE_DATE_NOT_ALLOWED = "No se permiten fechas futuras"

# Errores de negocio
BUSINESS_INSUFFICIENT_FUNDS = "Fondos insuficientes"
BUSINESS_ACCOUNT_INACTIVE = "La cuenta está inactiva"
BUSINESS_ACCOUNT_HAS_BALANCE = "No puede eliminar cuenta con balance"
BUSINESS_ACCOUNT_HAS_TRANSACTIONS = "No puede eliminar cuenta con transacciones"
BUSINESS_CATEGORY_IN_USE = "No puede eliminar categoría en uso"

# Errores de recursos no encontrados
NOT_FOUND_USER = "Usuario no encontrado"
NOT_FOUND_ACCOUNT = "Cuenta no encontrada"
NOT_FOUND_TRANSACTION = "Transacción no encontrada"
NOT_FOUND_CATEGORY = "Categoría no encontrada"

# Errores de servicios externos
EXTERNAL_SERVICE_UNAVAILABLE = "Servicio externo no disponible"
EXTERNAL_GEMINI_ERROR = "Error en el servicio de IA"
EXTERNAL_EMAIL_ERROR = "Error enviando email"

# Mensajes de éxito
SUCCESS_ACCOUNT_CREATED = "Cuenta creada exitosamente"
SUCCESS_ACCOUNT_UPDATED = "Cuenta actualizada exitosamente"
SUCCESS_ACCOUNT_DELETED = "Cuenta eliminada exitosamente"
SUCCESS_TRANSACTION_CREATED = "Transacción creada exitosamente"
SUCCESS_TRANSACTION_UPDATED = "Transacción actualizada exitosamente"
SUCCESS_TRANSACTION_DELETED = "Transacción eliminada exitosamente"
