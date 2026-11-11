from dataclasses import dataclass

from application.interfaces.auth_service import LoginThrottle


@dataclass(frozen=True, slots=True)
class LoginLocks:
    """Segundos de bloqueo que quedan (None = sin bloqueo)."""

    ip: int | None
    account: int | None


class LoginGuard:
    """Dos bloqueos tras fallar la contraseña, los dos en Redis:

    - Por correo + IP (`per_ip`): frena a quien prueba desde una IP sin dejar fuera al dueño,
      que entra desde otra.
    - Por correo (`per_account`), con un umbral mucho más alto: frena el ataque repartido
      entre muchas IPs. Un dispositivo que ya tuvo sesión en la cuenta se lo salta (lo decide
      el login), así que provocarlo no impide al dueño entrar desde sus aparatos.

    Aparte queda el rate limit por IP del endpoint, que cuenta todos los intentos.
    """

    def __init__(self, *, per_ip: LoginThrottle, per_account: LoginThrottle):
        self._per_ip = per_ip
        self._per_account = per_account

    @staticmethod
    def _ip_key(email: str, ip: str | None) -> str:
        return f"email:{email}:ip:{ip or 'unknown'}"

    @staticmethod
    def _account_key(email: str) -> str:
        return f"email:{email}"

    async def locks(self, email: str, ip: str | None) -> LoginLocks:
        return LoginLocks(
            ip=await self._per_ip.retry_after(self._ip_key(email, ip)),
            account=await self._per_account.retry_after(self._account_key(email)),
        )

    async def record_failure(self, email: str, ip: str | None) -> None:
        await self._per_ip.record_failure(self._ip_key(email, ip))
        await self._per_account.record_failure(self._account_key(email))

    async def succeeded(self, email: str, ip: str | None) -> None:
        await self._per_ip.reset(self._ip_key(email, ip))
        await self._per_account.reset(self._account_key(email))

    async def clear_account(self, email: str) -> None:
        """Tras restablecer la contraseña: el dueño no debe seguir bloqueado por el ataque."""
        await self._per_account.reset(self._account_key(email))
