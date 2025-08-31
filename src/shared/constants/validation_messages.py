"""Mensajes de validación multiidioma."""

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
        # Códigos específicos de Lunance - Conflictos de negocio
        "BUSINESS_EMAIL_EXISTS": "El email ya está registrado",
        "BUSINESS_ACCOUNT_HAS_BALANCE": "La cuenta tiene saldo pendiente",
        "BUSINESS_ACCOUNT_HAS_TRANSACTIONS": "La cuenta tiene transacciones asociadas",
        # Códigos específicos de Lunance - Validaciones y reglas de negocio
        "VALIDATION_ERROR": "Error de validación",
        "BUSINESS_RULE_VIOLATION": "Violación de regla de negocio",
        "VALIDATION_INVALID_AMOUNT": "Monto inválido",
        "INVALID_TRANSACTION_TYPE": "Tipo de transacción inválido",
        "VALIDATION_INVALID_CURRENCY": "Moneda inválida",
        "GEMINI_PROCESSING_ERROR": "Error procesando imagen con Gemini",
        "GEMINI_API_ERROR": "Error de API de Gemini",
        "VALIDATION_INVALID_IMAGE": "Imagen no válida o no procesable",
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
        # Códigos específicos de Lunance - Conflictos de negocio
        "BUSINESS_EMAIL_EXISTS": "Email already registered",
        "BUSINESS_ACCOUNT_HAS_BALANCE": "Account has pending balance",
        "BUSINESS_ACCOUNT_HAS_TRANSACTIONS": "Account has associated transactions",
        # Códigos específicos de Lunance - Validaciones y reglas de negocio
        "VALIDATION_ERROR": "Validation error",
        "BUSINESS_RULE_VIOLATION": "Business rule violation",
        "VALIDATION_INVALID_AMOUNT": "Invalid amount",
        "INVALID_TRANSACTION_TYPE": "Invalid transaction type",
        "VALIDATION_INVALID_CURRENCY": "Invalid currency",
        "GEMINI_PROCESSING_ERROR": "Error processing image with Gemini",
        "GEMINI_API_ERROR": "Gemini API error",
        "VALIDATION_INVALID_IMAGE": "Invalid or unprocessable image",
    },
}


def translate_validation_message(
    error_type: str, field_name: str = None, language: str = "es", **context
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
