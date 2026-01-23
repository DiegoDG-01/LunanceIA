"""Manejador global de excepciones para estandarizar respuestas de error."""

import logging
from typing import Union, Dict, Tuple, Type

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded
from shared.i18n.messages import get_error_message

from infrastructure.config.settings import settings

from shared.exceptions.base import (
    LunanceException,
    ValidationError as LunanceValidationError,
    UnauthorizedError,
    BusinessRuleError,
)
from shared.exceptions.domain import (
    UserNotFoundError,
    InvalidCredentialsError,
    UserInactiveError,
    EmailAlreadyExistsError,
    AccountNotFoundError,
    AccountInactiveError,
    AccountHasBalanceError,
    AccountHasTransactionsError,
    TransactionNotFoundError,
    InvalidTransactionAmountError,
    CategoryNotFoundError,
    InvalidCurrencyError,
    CurrencyMismatchError,
    NegativeAmountError,
    GeminiAPIError,
    GeminiProcessingError,
    GeminiInvalidResponseError,
    InvalidImageError,
    InvalidTransactionTypeError,
    InsufficientFundsError,
    SubscriptionNotFoundError,
)
from shared.exceptions.application import (
    JWTValidationError,
    CommandValidationError,
    QueryValidationError,
    RepositoryError,
    ExternalServiceError,
)
from presentation.schemas.responses.error import StandardErrorResponse, ErrorDetail
from shared.constants.validation_messages import (
    translate_validation_message,
    get_main_validation_message,
    get_http_code_error_message,
)
from shared.utils.language import get_user_language

logger = logging.getLogger(__name__)

# Definición del diccionario de mapeo
EXCEPTION_MAP: Dict[Type[Exception], Tuple[str, int]] = {
    # --- Autenticación y Autorización (401) ---
    InvalidCredentialsError: ("AUTH_INVALID_CREDENTIALS", 401),
    UnauthorizedError: ("AUTH_INVALID_CREDENTIALS", 401),
    UserInactiveError: ("AUTH_USER_INACTIVE", 401),
    JWTValidationError: ("JWT_VALIDATION_ERROR", 401),
    # --- Recursos No Encontrados (404) ---
    UserNotFoundError: ("NOT_FOUND_USER", 404),
    AccountNotFoundError: ("NOT_FOUND_ACCOUNT", 404),
    TransactionNotFoundError: ("NOT_FOUND_TRANSACTION", 404),
    CategoryNotFoundError: ("NOT_FOUND_CATEGORY", 404),
    SubscriptionNotFoundError: ("NOT_FOUND_SUBSCRIPTION", 404),
    # --- Conflictos de Negocio (409) ---
    EmailAlreadyExistsError: ("BUSINESS_EMAIL_EXISTS", 409),
    AccountHasBalanceError: ("BUSINESS_ACCOUNT_HAS_BALANCE", 409),
    AccountHasTransactionsError: ("BUSINESS_ACCOUNT_HAS_TRANSACTIONS", 409),
    # --- Errores de Validación y Reglas de Negocio (400 / 422) ---
    InsufficientFundsError: ("INSUFFICIENT_FUNDS", 422),
    AccountInactiveError: ("BUSINESS_RULE_VIOLATION", 400),
    InvalidTransactionAmountError: ("VALIDATION_INVALID_AMOUNT", 400),
    NegativeAmountError: ("VALIDATION_INVALID_AMOUNT", 400),
    InvalidTransactionTypeError: ("INVALID_TRANSACTION_TYPE", 400),
    InvalidCurrencyError: ("VALIDATION_INVALID_CURRENCY", 400),
    CurrencyMismatchError: ("VALIDATION_INVALID_CURRENCY", 400),
    CommandValidationError: ("VALIDATION_ERROR", 400),
    QueryValidationError: ("VALIDATION_ERROR", 400),
    LunanceValidationError: ("VALIDATION_ERROR", 400),
    BusinessRuleError: ("VALIDATION_ERROR", 400),
    # --- Errores de API Gemini ---
    GeminiProcessingError: ("GEMINI_PROCESSING_ERROR", 422),
    GeminiInvalidResponseError: ("GEMINI_PROCESSING_ERROR", 422),
    GeminiAPIError: ("GEMINI_API_ERROR", 503),
    InvalidImageError: ("VALIDATION_INVALID_IMAGE", 400),
    # --- Infraestructura y Servicios Externos (500 / 503) ---
    RepositoryError: ("INTERNAL_SERVER_ERROR", 500),
    ExternalServiceError: ("SERVICE_UNAVAILABLE", 503),
}


def map_exception_to_error_code(exc: Exception) -> tuple[str, int]:
    """
    Map a domain or system exception to a standardized error code and HTTP status.

    Parameters:
        exc (Exception): The exception instance to map.

    Returns:
        tuple[str, int]: A tuple containing the error code and corresponding HTTP status code.
    """

    exc_type = type(exc)

    if exc_type in EXCEPTION_MAP:
        return EXCEPTION_MAP[exc_type]

    for error_class, response in EXCEPTION_MAP.items():
        if isinstance(exc, error_class):
            return response

    return "INTERNAL_SERVER_ERROR", 500


async def lunance_exception_handler(
    request: Request, exc: LunanceException
) -> JSONResponse:
    """
    Handles custom Lunance exceptions and returns a standardized JSON error response.

    The handler maps the exception to an error code and HTTP status, logs the error, detects the user's language from the request, translates the error message, and constructs a consistent error response.
    """
    error_code, status_code = map_exception_to_error_code(exc)

    # Error logging for development and production
    if settings.ENVIRONMENT.upper() == "DEV":
        logger.error(f"LunanceException: {error_code} - {exc.message}", exc_info=exc)
    elif settings.ENVIRONMENT.upper() == "PROD":
        logger.warning(f"LunanceException: {error_code} - {exc.message}")

    # Detectar idioma del usuario
    user_language = get_user_language(request)

    # Traducir el mensaje al idioma del usuario
    translated_message = get_http_code_error_message(
        code=error_code, language=user_language
    )

    details_list = None
    if hasattr(exc, "details") and exc.details:
        details_list = []
        for detail in exc.details:
            msg = get_error_message(detail.get("type"), user_language)
            details_list.append(
                ErrorDetail(
                    loc=detail.get("loc"),
                    msg=msg,
                    type=detail.get("type"),
                    input=detail.get("input"),
                )
            )

    error_response = StandardErrorResponse(
        error_code=error_code, message=translated_message, details=details_list
    )

    return JSONResponse(status_code=status_code, content=error_response.model_dump())


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle FastAPI/Pydantic validation errors and return a standardized, localized error response.

    Extracts validation errors, translates each message based on the user's language, and returns a JSON response with detailed error information and a main validation error message.
    """
    logger.warning(f"Validation error: {exc.errors()}")

    # Detectar idioma del usuario
    user_language = get_user_language(request)

    # Convertir errores de Pydantic al formato estándar
    details = []
    for error in exc.errors():
        # Extraer información del error
        error_type = error.get("type", "validation_error")
        field_name = None

        # Obtener el nombre del campo de la ubicación
        loc = error.get("loc", [])
        if len(loc) > 1:  # ['body', 'field_name']
            field_name = loc[-1]  # Último elemento es el campo

        # Traducir el mensaje al idioma del usuario
        translated_msg = translate_validation_message(
            error_type=error_type,
            field_name=field_name,
            language=user_language,
            **error.get("ctx", {}),  # Contexto adicional para formateo
        )

        details.append(
            ErrorDetail(
                loc=error.get("loc"),
                msg=translated_msg,
                type=error_type,
                input=error.get("input"),
            )
        )

    # Mensaje principal en el idioma del usuario
    main_message = get_main_validation_message(user_language)

    error_response = StandardErrorResponse(
        error_code="VALIDATION_ERROR", message=main_message, details=details
    )

    return JSONResponse(status_code=422, content=error_response.model_dump())


async def http_exception_handler(
    request: Request, exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """
    Handle standard HTTP exceptions and return a standardized JSON error response.

    Maps the HTTP status code to a predefined error code, translates the error message based on the user's language, and returns a consistent error response structure with the original HTTP status code.
    """
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")

    # Mapear códigos HTTP a códigos de error
    error_code_mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }

    error_code = error_code_mapping.get(exc.status_code, "HTTP_ERROR")

    user_language = get_user_language(request)
    main_message = get_http_code_error_message(code=error_code, language=user_language)

    error_response = StandardErrorResponse(
        error_code=error_code, message=main_message, details=None
    )

    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump()
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handles uncaught exceptions and returns a standardized internal server error response in the user's language.

    Returns:
        JSONResponse: A JSON response with HTTP status 500 and a translated error message.
    """
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=exc
    )

    # Detectar idioma del usuario
    user_language = get_user_language(request)

    # Traducir el mensaje al idioma del usuario
    translated_message = get_http_code_error_message(
        code="INTERNAL_SERVER_ERROR", language=user_language
    )

    error_response = StandardErrorResponse(
        error_code="INTERNAL_SERVER_ERROR", message=translated_message, details=None
    )

    return JSONResponse(status_code=500, content=error_response.model_dump())


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """
    Handle rate limit exceeded errors and return a standardized JSON error response.

    Provides detailed information about the rate limit violation including the limit,
    remaining requests, and retry-after time in the user's preferred language.
    """
    logger.warning(f"Rate limit exceeded for {request.client.host}: {exc.detail}")

    # Detectar idioma del usuario
    user_language = get_user_language(request)

    # Traducir mensaje principal
    main_message = get_http_code_error_message(
        code="RATE_LIMIT_EXCEEDED", language=user_language
    )

    # Crear detalles específicos del rate limit
    details = []
    if hasattr(exc, "detail") and exc.detail:
        # Extraer información del rate limit del mensaje de error
        detail_msg = str(exc.detail)

        details.append(
            ErrorDetail(
                loc=["rate_limit"],
                msg=detail_msg,
                type="rate_limit_exceeded",
                input=None,
            )
        )

    error_response = StandardErrorResponse(
        error_code="RATE_LIMIT_EXCEEDED",
        message=main_message,
        details=details if details else None,
    )

    # Crear respuesta con headers de rate limiting
    response = JSONResponse(status_code=429, content=error_response.model_dump())

    # Agregar headers informativos si están disponibles en la excepción
    if hasattr(exc, "retry_after") and exc.retry_after:
        response.headers["Retry-After"] = str(exc.retry_after)

    # Headers estándar de rate limiting (versión corregida y segura)
    response.headers["X-RateLimit-Remaining"] = "0"

    # Intentar extraer límite del mensaje de error de manera segura
    try:
        detail_str = str(exc.detail) if hasattr(exc, "detail") and exc.detail else ""

        # slowapi suele tener mensajes como "Rate limit exceeded: 5 per 1 minute"
        if ":" in detail_str and "per" in detail_str:
            parts = detail_str.split(":")
            if len(parts) > 1:
                limit_part = parts[1].strip().split(" ")[0]
                response.headers["X-RateLimit-Limit"] = limit_part
            else:
                response.headers["X-RateLimit-Limit"] = "Unknown"
        else:
            response.headers["X-RateLimit-Limit"] = "Unknown"

    except Exception:
        # Sí hay cualquier error extrayendo la información, usar valor por defecto
        response.headers["X-RateLimit-Limit"] = "Unknown"

    return response
