import hashlib


def normalize_email(value: str) -> str:
    """Forma canónica de un correo: sin espacios alrededor y en minúsculas.

    Es la que se guarda en `users.email` y `pending_signups.email`, y la que se busca al
    iniciar sesión: `Ana@Example.com` y `ana@example.com` son la misma cuenta.
    """
    return value.strip().lower()


def email_digest(email: str) -> str:
    """Identificador del buzón para claves de Redis: el correo no llega a Redis en claro."""
    return hashlib.sha256(normalize_email(email).encode()).hexdigest()[:32]
