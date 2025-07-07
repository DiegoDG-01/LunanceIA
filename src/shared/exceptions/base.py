"""Excepciones base del sistema."""
class LunanceException(Exception):
    """Excepción base de la aplicación."""

    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


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
