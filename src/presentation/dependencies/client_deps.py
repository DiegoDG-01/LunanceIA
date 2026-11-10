"""Contexto del cliente para las rutas de sesión: dispositivo, plataforma, IP y user agent."""

from uuid import UUID

from fastapi import Header, Request
from fastapi.exceptions import RequestValidationError

from application.auth.dto import ClientContext
from domain.entities.auth.session import Platform
from infrastructure.rate_limiting.client_ip import client_ip

DEVICE_HEADER = "X-Lunance-Device"
CLIENT_HEADER = "X-Lunance-Client"
CLIENT_MAX_LENGTH = 50
USER_AGENT_MAX_LENGTH = 500


def parse_client(value: str | None) -> tuple[Platform, str | None]:
    """`<plataforma>/<versión>` (`web`, `ios` o `android`). Sin cabecera, es la web."""
    if value is None or not value.strip():
        return Platform.WEB, None
    value = value.strip()
    platform_name = value.split("/", 1)[0].strip().lower()
    try:
        platform = Platform(platform_name)
    except ValueError:
        platform = None
    if platform is None or len(value) > CLIENT_MAX_LENGTH:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("header", CLIENT_HEADER),
                    "msg": "Must be '<web|ios|android>/<version>'",
                    "input": value,
                    "ctx": {"error": "invalid client"},
                }
            ]
        )
    return platform, value


def _base_context(
    request: Request, client_header: str | None, device_id: UUID | None
) -> ClientContext:
    platform, client = parse_client(client_header)
    user_agent = request.headers.get("user-agent")
    return ClientContext(
        device_id=str(device_id) if device_id else None,
        platform=platform,
        client=client,
        ip=client_ip(request),
        user_agent=user_agent[:USER_AGENT_MAX_LENGTH] if user_agent else None,
    )


async def get_device_context(
    request: Request,
    device_id: UUID = Header(alias=DEVICE_HEADER),
    client: str | None = Header(default=None, alias=CLIENT_HEADER),
) -> ClientContext:
    """Login y refresh: el dispositivo es obligatorio (422 si falta o no es un UUID)."""
    return _base_context(request, client, device_id)


async def get_client_context(
    request: Request,
    client: str | None = Header(default=None, alias=CLIENT_HEADER),
) -> ClientContext:
    """Resto de rutas de sesión: el dispositivo no hace falta."""
    return _base_context(request, client, None)
