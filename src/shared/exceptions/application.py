"""Excepciones de la capa de aplicación."""

from shared.exceptions.base import JWTException, LunanceException, ValidationError


class JWTValidationError(JWTException):
    """Error de validación en JWT."""

    def __init__(self, message: str):
        super().__init__(message)


class CommandValidationError(ValidationError):
    """Error de validación en comando."""

    def __init__(self, command_name: str, validation_errors: list):
        message = f"Error de validación en comando {command_name}: {', '.join(validation_errors)}"
        detail = [
            {
                "loc": ["body", command_name],
                "msg": ", ".join(validation_errors),
                "type": "COMMAND_VALIDATION_ERROR",
            }
        ]
        super().__init__(message, detail)


class QueryValidationError(ValidationError):
    """Error de validación en query."""

    def __init__(self, query_name: str, validation_errors: list):
        message = (
            f"Error de validación en query {query_name}: {', '.join(validation_errors)}"
        )
        super().__init__(message)


class RepositoryError(LunanceException):
    """Error en repositorio."""

    def __init__(self, operation: str, entity: str, details: str = ""):
        message = f"Error en repositorio durante {operation} de {entity}"
        if details:
            message += f": {details}"
        super().__init__(message)


class ExternalServiceError(LunanceException):
    """Error en servicio externo."""

    def __init__(self, service_name: str, operation: str, details: str = ""):
        message = f"Error en servicio externo {service_name} durante {operation}"
        if details:
            message += f": {details}"
        super().__init__(message)


class IdempotencyKeyReusedError(LunanceException):
    """La misma Idempotency-Key llegó con otra petición (método, ruta o cuerpo).

    Es un error del cliente, no un reintento: la clave identifica una operación concreta.
    """

    def __init__(self):
        super().__init__("Idempotency-Key reutilizada con una petición distinta")


class IdempotencyKeyInUseError(LunanceException):
    """La clave existe pero su respuesta no está guardada.

    O la petición original sigue en curso, o el proceso murió entre el commit del
    cambio y el guardado de la respuesta. El cliente debe consultar el recurso antes
    de decidir si reintenta con una clave nueva.
    """

    def __init__(self):
        super().__init__(
            "La operación de esta Idempotency-Key no tiene respuesta guardada"
        )


class TooManyAttemptsError(LunanceException):
    """Demasiados intentos fallidos: el sujeto (correo, IP) está bloqueado unos segundos."""

    def __init__(self, retry_after: int):
        self.retry_after = max(1, int(retry_after))
        super().__init__(
            f"Demasiados intentos; vuelve a intentarlo en {self.retry_after} s"
        )


class ServiceTemporarilyUnavailableError(LunanceException):
    """Un servicio del que depende la protección de la ruta (Redis) no responde.

    Login, registro y recuperación de contraseña no se atienden sin su protección contra
    fuerza bruta: responden 503 con `Retry-After`.
    """

    def __init__(self, service_name: str, retry_after: int = 5):
        self.retry_after = retry_after
        super().__init__(f"Servicio {service_name} no disponible")
