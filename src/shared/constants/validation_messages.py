"""Mensajes de validación multiidioma."""

from typing import Optional

# Mapeo de mensajes de validación de Pydantic por idioma
PYDANTIC_ERROR_MESSAGES = {
    "es": {
        # String validations
        "string_too_short": "El texto debe tener al menos {min_length} caracteres",
        "string_too_long": "El texto no puede exceder {max_length} caracteres",
        "string_pattern_mismatch": "El formato no es válido",
        # Email validations
        "value_error": "Formato de email inválido",
        "value_error.email": "Formato de email inválido",
        "missing": "Este campo es requerido",
        # Number validations
        "type_error.integer": "Debe ser un número entero",
        "type_error.float": "Debe ser un número decimal",
        "value_error.number.not_gt": "El valor debe ser mayor a {gt}",
        "value_error.number.not_ge": "El valor debe ser mayor o igual a {ge}",
        "value_error.number.not_lt": "El valor debe ser menor a {lt}",
        "value_error.number.not_le": "El valor debe ser menor o igual a {le}",
        # Date validations
        "type_error.datetime": "Formato de fecha inválido",
        "value_error.datetime": "Fecha inválida",
        # Boolean validations
        "type_error.bool": "Debe ser verdadero o falso",
        # List validations
        "type_error.list": "Debe ser una lista",
        "value_error.list.min_items": "Debe contener al menos {limit_value} elementos",
        "value_error.list.max_items": "No puede contener más de {limit_value} elementos",
        # Dict validations
        "type_error.dict": "Debe ser un objeto",
        # Enum validations
        "type_error.enum": "Valor no válido. Opciones permitidas: {permitted}",
        # UUID validations
        "type_error.uuid": "Formato de UUID inválido",
        # JSON validations
        "value_error.jsondecode": "Formato JSON inválido",
        # Generic validations
        "type_error": "Tipo de dato inválido",
        "value_error.any_str.min_length": "Debe tener al menos {limit_value} caracteres",
        "value_error.any_str.max_length": "No puede exceder {limit_value} caracteres",
    },
    "en": {
        # String validations
        "string_too_short": "Text must have at least {min_length} characters",
        "string_too_long": "Text cannot exceed {max_length} characters",
        "string_pattern_mismatch": "Format is not valid",
        # Email validations
        "value_error": "Invalid email format",
        "value_error.email": "Invalid email format",
        "missing": "This field is required",
        # Number validations
        "type_error.integer": "Must be an integer",
        "type_error.float": "Must be a decimal number",
        "value_error.number.not_gt": "Value must be greater than {gt}",
        "value_error.number.not_ge": "Value must be greater than or equal to {ge}",
        "value_error.number.not_lt": "Value must be less than {lt}",
        "value_error.number.not_le": "Value must be less than or equal to {le}",
        # Date validations
        "type_error.datetime": "Invalid date format",
        "value_error.datetime": "Invalid date",
        # Boolean validations
        "type_error.bool": "Must be true or false",
        # List validations
        "type_error.list": "Must be a list",
        "value_error.list.min_items": "Must contain at least {limit_value} items",
        "value_error.list.max_items": "Cannot contain more than {limit_value} items",
        # Dict validations
        "type_error.dict": "Must be an object",
        # Enum validations
        "type_error.enum": "Invalid value. Allowed options: {permitted}",
        # UUID validations
        "type_error.uuid": "Invalid UUID format",
        # JSON validations
        "value_error.jsondecode": "Invalid JSON format",
        # Generic validations
        "type_error": "Invalid data type",
        "value_error.any_str.min_length": "Must have at least {limit_value} characters",
        "value_error.any_str.max_length": "Cannot exceed {limit_value} characters",
    },
}

# Mensajes específicos para campos comunes por idioma
FIELD_SPECIFIC_MESSAGES = {
    "es": {
        "email": "Formato de email inválido",
        "password": "La contraseña debe tener al menos 8 caracteres",
        "name": "El nombre es requerido y debe tener al menos 1 caracter",
        "amount": "El monto debe ser un número positivo",
        "currency": "Código de moneda inválido",
        "account_type": "Tipo de cuenta inválido",
        "description": "La descripción es demasiado larga",
    },
    "en": {
        "email": "Invalid email format",
        "password": "Password must be at least 8 characters",
        "name": "Name is required and must have at least 1 character",
        "amount": "Amount must be a positive number",
        "currency": "Invalid currency code",
        "account_type": "Invalid account type",
        "description": "Description is too long",
    },
}

# Mensajes principales por idioma
MAIN_MESSAGES = {
    "es": {
        "validation_errors": "Errores de validación en los datos enviados",
        "validation_error_default": "Error de validación",
    },
    "en": {
        "validation_errors": "Validation errors in submitted data",
        "validation_error_default": "Validation error",
    },
}

HTTP_CODES_ERRORS = {
    "es": {
        # Códigos HTTP genéricos
        "UNPROCESSABLE_ENTITY": "Los datos enviados no son válidos",
        "BAD_REQUEST": "Los datos enviados no son válidos",
        "NOT_FOUND": "El recurso no fue encontrado",
        "INTERNAL_SERVER_ERROR": "Ha ocurrido un error interno del servidor",
        "UNAUTHORIZED": "Acceso no autorizado",
        "FORBIDDEN": "Acceso prohibido",
        "METHOD_NOT_ALLOWED": "Método no permitido",
        "CONFLICT": "Conflicto en la solicitud",
        "RATE_LIMIT_EXCEEDED": "Límite de solicitudes excedido",
        "BAD_GATEWAY": "Error de puerta de enlace",
        "SERVICE_UNAVAILABLE": "Servicio no disponible",
        "HTTP_ERROR": "Error HTTP",
        # Códigos específicos de Lunance - Autenticación
        "AUTH_INVALID_CREDENTIALS": "Credenciales inválidas",
        "AUTH_USER_INACTIVE": "Usuario inactivo",
        # JWT Validation error
        "JWT_VALIDATION_ERROR": "Token inválido: malformado o expirado",
        # Códigos específicos de Lunance - Recursos no encontrados
        "NOT_FOUND_USER": "Usuario no encontrado",
        "NOT_FOUND_ACCOUNT": "Cuenta no encontrada",
        "NOT_FOUND_TRANSACTION": "Transacción no encontrada",
        "NOT_FOUND_CATEGORY": "Categoría no encontrada",
        "NOT_FOUND_SUBSCRIPTION": "Suscripción no encontrada",
        "NOT_FOUND_ACTIVITY": "No se encontró ningún movimiento",
        "INVESTMENT_SETTINGS_NOT_FOUND": "Configuración de cuenta no encontrada",
        # Códigos específicos de Lunance - Conflictos de negocio
        "BUSINESS_EMAIL_EXISTS": "El email ya está registrado",
        "BUSINESS_ACCOUNT_HAS_BALANCE": "La cuenta tiene saldo pendiente",
        "BUSINESS_ACCOUNT_HAS_TRANSACTIONS": "La cuenta tiene transacciones asociadas",
        "INVALID_ACCOUNT_SETTINGS": "Los datos adicionales para configurar tu cuenta no son los correctos",
        # Códigos específicos de Lunance - Validaciones y reglas de negocio
        "VALIDATION_ERROR": "Error de validación",
        "BUSINESS_RULE_VIOLATION": "Violación de regla de negocio",
        "VALIDATION_INVALID_AMOUNT": "Monto inválido",
        "INVALID_TRANSACTION_TYPE": "Tipo de transacción inválido",
        "VALIDATION_INVALID_CURRENCY": "Moneda inválida",
        "AI_PROCESSING_ERROR": "Error procesando datos con el servicio de IA",
        "AI_SERVICE_ERROR": "Error de servicio de IA",
        "VALIDATION_INVALID_IMAGE": "Imagen no válida o no procesable",
        "INSUFFICIENT_FUNDS": "Fondos insuficientes",
        "VALIDATION_INVALID_INVESTMENT_RATE": "La tasa de inversión debe ser no negativa",
        "VALIDATION_INVALID_PENALTY_PERCENTAGE": "El porcentaje de penalización debe estar entre 0 y 100",
        "VALIDATION_INVALID_INVESTMENT_TYPE": "Tipo de inversión inválido",
        "VALIDATION_INVALID_BILLING_CYCLE_DAY": "El día de ciclo de facturación debe estar entre 1 y 31",
        "VALIDATION_INVALID_PAYMENT_DUE_DAY": "El día de vencimiento de pago debe estar entre 1 y  31",
        "VALIDATION_INVALID_CREDIT_LIMIT": "El límite de crédito debe ser positivo",
        "VALIDATION_INVALID_MINIMUM_PAYMENT": "El porcentaje de pago mínimo debe estar entre 0 y 100",
        "VALIDATION_INVALID_EMAIL": "Formato de email inválido",
        "VALIDATION_INVALID_BALANCE_UPDATE": "No se puede actualizar el balance de la cuenta",
    },
    "en": {
        # Códigos HTTP genéricos
        "UNPROCESSABLE_ENTITY": "The submitted data is not valid",
        "BAD_REQUEST": "The submitted data is not valid",
        "NOT_FOUND": "The resource was not found",
        "INTERNAL_SERVER_ERROR": "An internal server error occurred",
        "UNAUTHORIZED": "Unauthorized access",
        "FORBIDDEN": "Forbidden access",
        "METHOD_NOT_ALLOWED": "Method not allowed",
        "CONFLICT": "Conflict in request",
        "RATE_LIMIT_EXCEEDED": "Rate limit exceeded",
        "BAD_GATEWAY": "Bad gateway error",
        "SERVICE_UNAVAILABLE": "Service unavailable",
        "HTTP_ERROR": "HTTP error",
        # Códigos específicos de Lunance - Autenticación
        "AUTH_INVALID_CREDENTIALS": "Invalid credentials",
        "AUTH_USER_INACTIVE": "Inactive user",
        # JWT Validation error
        "JWT_VALIDATION_ERROR": "Invalid token: malformed or expired",
        # Códigos específicos de Lunance - Recursos no encontrados
        "NOT_FOUND_USER": "User not found",
        "NOT_FOUND_ACCOUNT": "Account not found",
        "NOT_FOUND_TRANSACTION": "Transaction not found",
        "NOT_FOUND_CATEGORY": "Category not found",
        "NOT_FOUND_SUBSCRIPTION": "Subscription not found",
        "INVESTMENT_SETTINGS_NOT_FOUND": "Account settings not found",
        "NOT_FOUND_ACTIVITY": "No movement was found",
        # Códigos específicos de Lunance - Conflictos de negocio
        "INVALID_CREDENTIALS": "Invalid credentials",
        "BUSINESS_EMAIL_EXISTS": "Email already registered",
        "BUSINESS_ACCOUNT_HAS_BALANCE": "Account has pending balance",
        "BUSINESS_ACCOUNT_HAS_TRANSACTIONS": "Account has associated transactions",
        "INVALID_ACCOUNT_SETTINGS": "The additional information you provided to set up your account is incorrect",
        # Códigos específicos de Lunance - Validaciones y reglas de negocio
        "VALIDATION_ERROR": "Validation error",
        "BUSINESS_RULE_VIOLATION": "Business rule violation",
        "VALIDATION_INVALID_AMOUNT": "Invalid amount",
        "INVALID_TRANSACTION_TYPE": "Invalid transaction type",
        "VALIDATION_INVALID_CURRENCY": "Invalid currency",
        "AI_PROCESSING_ERROR": "Error processing data with AI service",
        "AI_SERVICE_ERROR": "AI service error",
        "VALIDATION_INVALID_IMAGE": "Invalid or unprocessable image",
        "INSUFFICIENT_FUNDS": "Insufficient funds",
        "VALIDATION_INVALID_INVESTMENT_RATE": "Interest rate must be non negative",
        "VALIDATION_INVALID_PENALTY_PERCENTAGE": "Early withdrawal penalty must be between 0 and 100",
        "VALIDATION_INVALID_INVESTMENT_TYPE": "Invalid investment type",
        "VALIDATION_INVALID_BILLING_CYCLE_DAY": "Billing cycle day must be between 1 and 31",
        "VALIDATION_INVALID_PAYMENT_DUE_DAY": "Payment due day must be between 1 and 31",
        "VALIDATION_INVALID_CREDIT_LIMIT": "Credit limit must be positive",
        "VALIDATION_INVALID_MINIMUM_PAYMENT": "Minimum payment percentage must be between 0 and 100",
        "VALIDATION_INVALID_EMAIL": "Invalid email format",
        "VALIDATION_INVALID_BALANCE_UPDATE": "Cannot update account balance",
    },
}

ERROR_DETAIL_MESSAGES = {
    "es": {
        "EMAIL_REQUIRED": "El email es requerido",
        "EMAIL_INVALID_FORMAT": "Formato de email inválido",
        "PASSWORD_REQUIRED": "La contraseña es requerida",
        "PASSWORD_TOO_SHORT": "La contraseña debe tener al menos 8 caracteres",
        "PASSWORD_MISSING_UPPERCASE": "La contraseña debe incluir al menos una mayúscula",
        "PASSWORD_MISSING_LOWERCASE": "La contraseña debe incluir al menos una minúscula",
        "PASSWORD_MISSING_DIGIT": "La contraseña debe incluir al menos un número",
        "PASSWORD_MISSING_SPECIAL": "La contraseña debe incluir al menos un carácter especial",
        "REFRESH_TOKEN_INVALID": "El token de refresco es inválido",
        "INSUFFICIENT_FUNDS": "Fondos insuficientes",
        "INVALID_TYPE": "Tipo de valor invalido",
        "BUSINESS_RULE_VIOLATION": "La operación no pudo completarse debido a una restricción",
        "COMMAND_VALIDATION_ERROR": "Error de validación en el comando",
    },
    "en": {
        "EMAIL_REQUIRED": "Email is required",
        "EMAIL_INVALID_FORMAT": "Invalid email format",
        "PASSWORD_REQUIRED": "Password is required",
        "PASSWORD_TOO_SHORT": "Password must be at least 8 characters",
        "PASSWORD_MISSING_UPPERCASE": "Password must include at least one uppercase letter",
        "PASSWORD_MISSING_LOWERCASE": "Password must include at least one lowercase letter",
        "PASSWORD_MISSING_DIGIT": "Password must include at least one number",
        "PASSWORD_MISSING_SPECIAL": "Password must include at least one special character",
        "REFRESH_TOKEN_INVALID": "Refresh token is invalid",
        "INSUFFICIENT_FUNDS": "Insufficient funds",
        "INVALID_TYPE": "Invalid typo of value",
        "BUSINESS_RULE_VIOLATION": "The operation could not be completed due to a restriction",
        "COMMAND_VALIDATION_ERROR": "Command validation error",
    },
}


def get_error_detail_message(code: str, language: str = "es") -> str:
    """
    Obtiene el mensaje de detalle de error traducido.

    Args:
        code: Código del mensaje de error
        language: Idioma ("es" o "en")

    Returns:
        str: Mensaje traducido
    """
    if language not in ["es", "en"]:
        language = "es"

    return ERROR_DETAIL_MESSAGES[language].get(code, code)


def translate_validation_message(
    error_type: str, field_name: Optional[str] = None, language: str = "es", **context
) -> str:
    """
    Translates a Pydantic validation error message into the specified language, formatting it with provided context.

    If a field-specific message exists for the given field name, it is returned; otherwise, the general error type message is used. Defaults to Spanish if the language is unsupported. If message formatting fails due to missing context, the unformatted template is returned.

    Parameters:
        error_type (str): The Pydantic error type to translate.
        field_name (str, optional): The name of the field associated with the error.
        language (str, optional): The target language code ("es" or "en"). Defaults to "es".
        **context: Additional variables for message formatting.

    Returns:
        str: The localized and formatted validation error message.
    """
    # Validar idioma
    if language not in ["es", "en"]:
        language = "es"  # Default a español

    # Primero verificar si hay un mensaje específico para el campo
    field_messages = FIELD_SPECIFIC_MESSAGES.get(language, {})
    if field_name and field_name in field_messages:
        return field_messages[field_name]

    # Obtener el mensaje base del mapeo por idioma
    language_messages = PYDANTIC_ERROR_MESSAGES.get(language, {})
    message_template = language_messages.get(
        error_type, MAIN_MESSAGES[language]["validation_error_default"]
    )

    # Formatear el mensaje con el contexto proporcionado
    try:
        return message_template.format(**context)
    except (KeyError, ValueError):
        # Si falla el formateo, devolver el mensaje sin formatear
        return message_template


def get_http_code_error_message(code: str, language: str = "es") -> str:
    """
    Return the localized error message for a given HTTP status or application-specific error code.

    Parameters:
        code (str): The HTTP status or application-specific error code.
        language (str, optional): Language code ("es" or "en"). Defaults to "es".

    Returns:
        str: The translated error message, or the default validation error message if the code is not found.
    """
    if language not in ["es", "en"]:
        language = "es"

    return HTTP_CODES_ERRORS[language].get(
        code, MAIN_MESSAGES[language]["validation_error_default"]
    )


def get_main_validation_message(language: str = "es") -> str:
    """
    Return the main validation errors summary message in the specified language.

    Parameters:
        language (str): Language code ("es" for Spanish or "en" for English). Defaults to "es".

    Returns:
        str: Localized main validation errors summary message.
    """
    if language not in ["es", "en"]:
        language = "es"

    return MAIN_MESSAGES[language]["validation_errors"]
