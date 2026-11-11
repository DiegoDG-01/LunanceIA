"""Helpers para los flujos con correo: registrar y confirmar por la API, leer el token del
enlace que llegó al buzón en memoria."""

import re
import uuid

import httpx

from application.interfaces.email import OutgoingEmail
from infrastructure.external_services.email.memory import InMemoryEmailSender

PASSWORD = "Password123!"

_TOKEN = re.compile(r"[?&]token=([A-Za-z0-9_\-]+)")


def token_from(email: OutgoingEmail) -> str:
    match = _TOKEN.search(email.text)
    assert match, f"el correo '{email.subject}' no trae ningún enlace con token"
    return match.group(1)


def last_email_to(outbox: InMemoryEmailSender, address: str) -> OutgoingEmail:
    sent = outbox.sent_to(address)
    assert sent, f"no se mandó ningún correo a {address}"
    return sent[-1]


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


async def signup(
    http: httpx.AsyncClient,
    outbox: InMemoryEmailSender,
    *,
    email: str | None = None,
    username: str | None = None,
    password: str = PASSWORD,
) -> str:
    """Registro + confirmación por la API. Devuelve el correo (normalizado) de la cuenta."""
    email = email or unique_email()
    username = username or f"u_{uuid.uuid4().hex[:10]}"
    response = await http.post(
        "/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert response.status_code == 202, response.text
    token = token_from(last_email_to(outbox, email.strip().lower()))
    verified = await http.post("/auth/email/verify", json={"token": token})
    assert verified.status_code == 200, verified.text
    return email.strip().lower()
