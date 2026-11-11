from dataclasses import dataclass, field
from datetime import timedelta

from domain.entities.auth.session import Platform, SessionLifetime


@dataclass(frozen=True, slots=True)
class AuthConfig:
    web_session: SessionLifetime
    mobile_session: SessionLifetime
    # Repetir un refresh ya canjeado dentro de esta ventana no se trata como robo: cubre la
    # respuesta que se pierde por la red justo después de rotar.
    refresh_reuse_grace: timedelta
    # Deriva el sucesor de cada refresh token (HMAC). No va en el repr.
    refresh_rotation_key: bytes = field(repr=False)

    def lifetime_for(self, platform: Platform) -> SessionLifetime:
        return self.mobile_session if platform.is_mobile else self.web_session


@dataclass(frozen=True, slots=True)
class EmailAuthConfig:
    """Registro con correo y recuperación de contraseña."""

    # Base de los enlaces de los correos: `<base>/verify-email?token=…`.
    link_base_url: str
    # Lo que vale cada enlace de verificación (sin pasar de la vida del registro).
    email_verification_ttl: timedelta
    # Sin confirmar, el registro se olvida: el correo y el username quedan libres.
    pending_signup_ttl: timedelta
    password_reset_ttl: timedelta
