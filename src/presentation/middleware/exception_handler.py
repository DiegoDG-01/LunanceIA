"""Manejador global de excepciones para estandarizar respuestas de error."""

import logging
from typing import Union

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    """Mapea una excepción a su código de error y status HTTP correspondiente."""

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
    """Manejador para excepciones personalizadas de Lunance."""
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
    """Manejador para errores de validación de FastAPI/Pydantic."""
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
    """Manejador para HTTPException estándar."""
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
    """Manejador para excepciones no controladas."""
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
