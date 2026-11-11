"""Refresh token de Sign in with Apple: se guarda cifrado y solo sirve para revocar la
autorización de Lunance en la cuenta de Apple del usuario.

Apple exige revocarlo cuando el usuario borra su cuenta (guideline 5.1.1(v)); el borrado de
cuenta todavía no existe, pero `AppleAuthorizationRevoker.revoke_for_user` ya deja lista esa
parte.
"""

import json
import logging

from application.interfaces.identity_providers import (
    AppleSignInGateway,
    AppleTokens,
    SecretCipher,
)
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import IdentityProviderUnavailableError

logger = logging.getLogger(__name__)


def _context(user_id: int) -> str:
    return f"users:{user_id}:apple_refresh_token"


class AppleTokenVault:
    """Cifra el token con el client ID con el que se canjeó (la revocación usa el mismo)."""

    def __init__(self, *, cipher: SecretCipher, user_repository: UserRepository):
        self.cipher = cipher
        self.users = user_repository

    async def store(self, user_id: int, tokens: AppleTokens) -> None:
        """Sustituye el guardado. No hace commit."""
        payload = json.dumps(
            {"client_id": tokens.client_id, "refresh_token": tokens.refresh_token}
        )
        await self.users.set_apple_refresh_token(
            user_id, self.cipher.encrypt(payload, context=_context(user_id))
        )

    async def load(self, user_id: int) -> AppleTokens | None:
        """El token guardado, o None si no hay o no se puede descifrar (clave cambiada)."""
        stored = await self.users.get_apple_refresh_token(user_id)
        if not stored:
            return None
        try:
            payload = json.loads(self.cipher.decrypt(stored, context=_context(user_id)))
            return AppleTokens(
                refresh_token=str(payload["refresh_token"]),
                client_id=str(payload["client_id"]),
            )
        except (ValueError, KeyError, TypeError):
            logger.error(
                "Stored Apple refresh token cannot be decrypted",
                extra={"user_id": user_id},
            )
            return None

    async def clear(self, user_id: int) -> None:
        await self.users.set_apple_refresh_token(user_id, None)


class AppleAuthorizationRevoker:
    """Quita la autorización de Lunance en la cuenta de Apple del usuario."""

    def __init__(self, *, vault: AppleTokenVault, apple: AppleSignInGateway):
        self.vault = vault
        self.apple = apple

    async def revoke_for_user(self, user_id: int) -> bool:
        """Revoca en Apple el token guardado y lo borra de la fila (sin commit: lo hace quien
        llama, p. ej. el borrado de cuenta). False si no había token. Lanza
        `IdentityProviderUnavailableError` si Apple no responde; entonces no borra nada para
        poder reintentar."""
        tokens = await self.vault.load(user_id)
        if tokens is None:
            await self.vault.clear(user_id)
            return False
        await self.apple.revoke(tokens.refresh_token, client_id=tokens.client_id)
        await self.vault.clear(user_id)
        return True

    async def revoke_quietly(self, tokens: AppleTokens) -> bool:
        """Revocación de mejor esfuerzo de un token ya retirado de la base (al desvincular
        Apple): si Apple no responde solo queda en el log."""
        try:
            await self.apple.revoke(tokens.refresh_token, client_id=tokens.client_id)
        except IdentityProviderUnavailableError:
            logger.warning("Apple did not answer the token revocation")
            return False
        return True
