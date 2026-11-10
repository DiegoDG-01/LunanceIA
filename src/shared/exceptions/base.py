"""Excepciones base del sistema."""


class LunanceException(Exception):
    """Excepción base de la aplicación."""

    def __init__(self, message: str, details: list | None = None):
        self.message = message
        self.details = details
        super().__init__(message, details)


class JWTException(LunanceException):
    """Error de JWT."""


class ValidationError(LunanceException):
    """Error de validación."""


class NotFoundError(LunanceException):
    """Error cuando no se encuentra un recurso."""


class UnauthorizedError(LunanceException):
    """Error de autorización."""


class BusinessRuleError(LunanceException):
    """Error de regla de negocio."""
