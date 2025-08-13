"""Manejador global de excepciones para estandarizar respuestas de error."""

import logging
from typing import Union

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded

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
    InsufficientFundsError,
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
)
from presentation.schemas.responses.error import StandardErrorResponse, ErrorDetail
from shared.constants.validation_messages import (
    translate_validation_message,
    get_main_validation_message,
    get_http_code_error_message,
)
from shared.utils.language import get_user_language

logger = logging.getLogger(__name__)


def map_exception_to_error_code(exc: Exception) -> tuple[str, int]:
    """
    Map a domain or system exception to a standardized error code and HTTP status.

    Parameters:
        exc (Exception): The exception instance to map.

    Returns:
        tuple[str, int]: A tuple containing the error code and corresponding HTTP status code.
    """

    # Excepciones de autenticación y autorización (401)
    if isinstance(exc, (InvalidCredentialsError, UnauthorizedError)):
        return "AUTH_INVALID_CREDENTIALS", 401
    elif isinstance(exc, UserInactiveError):
        return "AUTH_USER_INACTIVE", 401

    # Excepciones de recursos no encontrados (404)
    elif isinstance(exc, UserNotFoundError):
        return "NOT_FOUND_USER", 404
    elif isinstance(exc, AccountNotFoundError):
        return "NOT_FOUND_ACCOUNT", 404
    elif isinstance(exc, TransactionNotFoundError):
        return "NOT_FOUND_TRANSACTION", 404
    elif isinstance(exc, CategoryNotFoundError):
        return "NOT_FOUND_CATEGORY", 404

    # Conflictos de negocio (409)
    elif isinstance(exc, EmailAlreadyExistsError):
        return "BUSINESS_EMAIL_EXISTS", 409
    elif isinstance(exc, AccountHasBalanceError):
        return "BUSINESS_ACCOUNT_HAS_BALANCE", 409
    elif isinstance(exc, AccountHasTransactionsError):
        return "BUSINESS_ACCOUNT_HAS_TRANSACTIONS", 409

    # Errores de validación y reglas de negocio (400)
    elif isinstance(exc, (LunanceValidationError, BusinessRuleError)):
        return "VALIDATION_ERROR", 400
    elif isinstance(exc, (InsufficientFundsError, AccountInactiveError)):
        return "BUSINESS_RULE_VIOLATION", 400
    elif isinstance(exc, (InvalidTransactionAmountError, NegativeAmountError)):
        return "VALIDATION_INVALID_AMOUNT", 400
    elif isinstance(exc, (InvalidCurrencyError, CurrencyMismatchError)):
        return "VALIDATION_INVALID_CURRENCY", 400

    # Errores de API Gemini
    elif isinstance(exc, (GeminiProcessingError, GeminiInvalidResponseError)):
        return "GEMINI_PROCESSING_ERROR", 422
    elif isinstance(exc, GeminiAPIError):
        return "GEMINI_API_ERROR", 503  # Service unavailable
    elif isinstance(exc, InvalidImageError):
        return "VALIDATION_INVALID_IMAGE", 400

    # Error genérico del sistema (500)
    else:
        return "INTERNAL_SERVER_ERROR", 500


async def lunance_exception_handler(
    request: Request, exc: LunanceException
) -> JSONResponse:
    """
    Handles custom Lunance exceptions and returns a standardized JSON error response.

    The handler maps the exception to an error code and HTTP status, logs the error, detects the user's language from the request, translates the error message, and constructs a consistent error response.
    """
    error_code, status_code = map_exception_to_error_code(exc)

    # Log del error para debugging
    logger.error(f"LunanceException: {error_code} - {exc.message}", exc_info=exc)

    # Detectar idioma del usuario
    user_language = get_user_language(request)

    # Traducir el mensaje al idioma del usuario
    translated_message = get_http_code_error_message(
        code=error_code, language=user_language
    )

    error_response = StandardErrorResponse(
        error_code=error_code, message=translated_message, details=None
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
        # Si hay cualquier error extrayendo la información, usar valor por defecto
        response.headers["X-RateLimit-Limit"] = "Unknown"

    return response
