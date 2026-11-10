import asyncio
import secrets

import bcrypt
from argon2 import PasswordHasher as _Argon2
from argon2 import Type
from argon2.exceptions import InvalidHashError, VerificationError

from application.interfaces.auth_service import PasswordHasher

_BCRYPT_PREFIX = "$2"


class Argon2PasswordHasher(PasswordHasher):
    """Argon2id (m=64 MiB, t=3, p=1). Verifica también los hashes bcrypt heredados (`$2…`):
    `needs_rehash` los marca para guardarlos con Argon2 en el siguiente login correcto.

    El hash es deliberadamente caro, así que corre en un hilo para no bloquear el event loop.
    """

    def __init__(
        self,
        *,
        time_cost: int = 3,
        memory_cost_kib: int = 64 * 1024,
        parallelism: int = 1,
    ) -> None:
        self._hasher = _Argon2(
            time_cost=time_cost,
            memory_cost=memory_cost_kib,
            parallelism=parallelism,
            type=Type.ID,
        )
        self._dummy_hash: str | None = None

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._hasher.hash, password)

    async def verify(self, password: str, password_hash: str) -> bool:
        if password_hash.startswith(_BCRYPT_PREFIX):
            return await asyncio.to_thread(_bcrypt_verify, password, password_hash)
        try:
            return await asyncio.to_thread(self._hasher.verify, password_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        if password_hash.startswith(_BCRYPT_PREFIX):
            return True
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except InvalidHashError:
            return True

    async def verify_dummy(self, password: str) -> None:
        if self._dummy_hash is None:
            self._dummy_hash = await self.hash(secrets.token_urlsafe(16))
        await self.verify(password, self._dummy_hash)


def _bcrypt_verify(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False
