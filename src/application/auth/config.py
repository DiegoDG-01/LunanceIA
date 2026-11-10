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
