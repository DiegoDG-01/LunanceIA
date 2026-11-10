"""Header `Idempotency-Key` para los tests de escritura.

Los POST que crean recursos lo exigen; cada llamada de test es una operación nueva,
así que lleva su propia clave. Los tests que prueban reintentos pasan `key=` explícita.
"""

from uuid import uuid4

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"


def with_idempotency_key(
    headers: dict[str, str], key: str | None = None
) -> dict[str, str]:
    """Copia `headers` añadiendo una Idempotency-Key (nueva salvo que se pase `key`)."""
    return {**headers, IDEMPOTENCY_KEY_HEADER: key or str(uuid4())}
