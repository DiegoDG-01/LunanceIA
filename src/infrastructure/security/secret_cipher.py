"""Cifrado de secretos guardados en la base (el refresh token de Apple) con AES-256-GCM.

La clave se deriva con HKDF-SHA256 del secreto de settings (`APPLE_TOKEN_ENCRYPTION_KEY`):
el valor del .env no se usa tal cual y cada propósito tiene su propia clave. Formato:
`v1.<base64url(nonce de 12 bytes + texto cifrado + tag)>`. El `context` (p. ej. el id del
usuario) va como dato asociado: el texto cifrado copiado a otra fila no se descifra.
"""

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from application.interfaces.identity_providers import SecretCipher

VERSION = "v1"
_NONCE_BYTES = 12
MIN_SECRET_LENGTH = 32


def derive_key(secret: str, purpose: str) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"lunance:secret-cipher",
        info=f"lunance:{purpose}:{VERSION}".encode(),
    ).derive(secret.encode())


class AesGcmSecretCipher(SecretCipher):
    def __init__(self, secret: str, *, purpose: str) -> None:
        if len(secret) < MIN_SECRET_LENGTH:
            raise ValueError(
                f"La clave de cifrado debe tener al menos {MIN_SECRET_LENGTH} caracteres"
            )
        self._aead = AESGCM(derive_key(secret, purpose))

    def encrypt(self, plaintext: str, *, context: str) -> str:
        nonce = os.urandom(_NONCE_BYTES)
        sealed = self._aead.encrypt(nonce, plaintext.encode(), context.encode())
        encoded = base64.urlsafe_b64encode(nonce + sealed).decode().rstrip("=")
        return f"{VERSION}.{encoded}"

    def decrypt(self, ciphertext: str, *, context: str) -> str:
        version, _, encoded = ciphertext.partition(".")
        if version != VERSION or not encoded:
            raise ValueError("Formato de texto cifrado desconocido")
        try:
            raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            nonce, sealed = raw[:_NONCE_BYTES], raw[_NONCE_BYTES:]
            return self._aead.decrypt(nonce, sealed, context.encode()).decode()
        except (InvalidTag, ValueError) as error:
            raise ValueError("No se pudo descifrar el secreto") from error
