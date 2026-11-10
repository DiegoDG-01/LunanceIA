"""IP del cliente para rate limits y logs.

Detrás de un proxy (Cloudflare), `request.client.host` es la IP del proxy: todos los usuarios
compartirían el mismo contador. `CLIENT_IP_HEADER` indica qué cabecera trae la IP real (por
ejemplo `CF-Connecting-IP`). Solo debe configurarse si el origen únicamente acepta tráfico de
ese proxy; si no, cualquiera podría falsificar la cabecera y saltarse el límite.
"""

import ipaddress

from fastapi import Request

from infrastructure.config.settings import settings


def client_ip(request: Request) -> str | None:
    header = settings.CLIENT_IP_HEADER
    if header:
        forwarded = request.headers.get(header, "").strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else None


def ip_identity(request: Request) -> str:
    """Identidad para contar peticiones por IP.

    IPv6 se agrupa por /64, el bloque que se le asigna entero a cada casa o línea móvil:
    contar por dirección permitiría saltarse el límite cambiando de una a otra dentro del bloque.
    """
    ip = client_ip(request)
    try:
        address = ipaddress.ip_address(ip or "")
    except ValueError:
        return f"ip:{ip or 'unknown'}"
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped:
            return f"ip:{address.ipv4_mapped}"
        return f"ip:{ipaddress.IPv6Network((address, 64), strict=False)}"
    return f"ip:{address}"
