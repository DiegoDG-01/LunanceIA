"""Excepciones base del sistema."""

from typing import Optional


class LunanceException(Exception):
    """Excepción base de la aplicación."""

    def __init__(self, message: str, details: Optional[list] = None):
        self.message = message
        self.details = details
        super().__init__(message, details)


class JWTException(LunanceException):
    """Error de JWT."""

    pass


class ValidationError(LunanceException):
    """Error de validación."""

    pass


class NotFoundError(LunanceException):
    """Error cuando no se encuentra un recurso."""

    pass


class UnauthorizedError(LunanceException):
    """Error de autorización."""

    pass


class BusinessRuleError(LunanceException):
    """Error de regla de negocio."""

    pass
