from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PendingSignup:
    """Registro a la espera del enlace del correo. La cuenta (`users`) no existe hasta que se
    abre: nadie se queda con un correo que no es suyo. Mientras sigue abierto reserva el
    username; caducado, el correo y el username quedan libres.

    Solo guarda el hash de la contraseña elegida.
    """

    email: str
    username: str
    password_hash: str
    created_at: datetime
    expires_at: datetime
    id: int | None = None

    def is_open(self, now: datetime) -> bool:
        return now < self.expires_at


@dataclass(frozen=True, slots=True)
class EmailVerificationToken:
    """Un enlace enviado para un registro (el primero y cada reenvío). Todos valen hasta
    caducar; al confirmar se borran con el registro, así que cada uno sirve una sola vez.
    Solo se guarda el SHA-256 del token."""

    token_hash: str
    pending_signup_id: int
    created_at: datetime
    expires_at: datetime

    def is_usable(self, now: datetime) -> bool:
        return now < self.expires_at
