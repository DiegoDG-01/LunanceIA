"""Excepciones de la capa de aplicación."""

from shared.exceptions.base import LunanceException, ValidationError, JWTException


class JWTValidationError(JWTException):
    """Error de validación en JWT."""

    def __init__(self, message: str):
        super().__init__(message, "JWT_VALIDATION_ERROR")


class CommandValidationError(ValidationError):
    """Error de validación en comando."""

    def __init__(self, command_name: str, validation_errors: list):
        message = f"Error de validación en comando {command_name}: {', '.join(validation_errors)}"
        super().__init__(message, "COMMAND_VALIDATION_ERROR")


class QueryValidationError(ValidationError):
    """Error de validación en query."""

    def __init__(self, query_name: str, validation_errors: list):
        message = (
            f"Error de validación en query {query_name}: {', '.join(validation_errors)}"
        )
        super().__init__(message, "QUERY_VALIDATION_ERROR")


class RepositoryError(LunanceException):
    """Error en repositorio."""

    def __init__(self, operation: str, entity: str, details: str = ""):
        message = f"Error en repositorio durante {operation} de {entity}"
        if details:
            message += f": {details}"
        super().__init__(message, "REPOSITORY_ERROR")


class ExternalServiceError(LunanceException):
    """Error en servicio externo."""

    def __init__(self, service_name: str, operation: str, details: str = ""):
        message = f"Error en servicio externo {service_name} durante {operation}"
        if details:
            message += f": {details}"
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")
