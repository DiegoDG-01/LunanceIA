"""Genera los secretos de autenticación que `Settings` exige sin valor por defecto.

    uv run python scripts/generate_secrets.py >> .env

Las claves PEM salen en una sola línea con `\\n` escapados y entre comillas simples, que es la
forma que entienden igual python-dotenv, docker compose y los gestores de secretos.
Cambiar `JWT_*` invalida todos los access tokens emitidos; cambiar `REFRESH_ROTATION_KEY`
obliga a todos los dispositivos a volver a iniciar sesión.
"""

import secrets

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _one_line(pem: bytes) -> str:
    return pem.decode().strip().replace("\n", "\\n")


def main() -> None:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    print(f"JWT_PRIVATE_KEY='{_one_line(private_pem)}'")
    print(f"JWT_PUBLIC_KEY='{_one_line(public_pem)}'")
    print(f"REFRESH_ROTATION_KEY='{secrets.token_urlsafe(48)}'")


if __name__ == "__main__":
    main()
