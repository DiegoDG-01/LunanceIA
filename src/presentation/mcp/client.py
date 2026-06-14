import httpx

from presentation.mcp.config import mcp_settings
from mcp.server.fastmcp import Context


_client = httpx.AsyncClient(
    base_url=f"{mcp_settings.LUNANCE_API_BASE_URL}/api/v2",
    timeout=httpx.Timeout(20.0),
    follow_redirects=True,  # sigue el 307 de FastAPI por barra final (mismo host conserva headers)
)


def get_client() -> httpx.AsyncClient:
    return _client


def get_api_key(ctx: Context) -> str:
    request = ctx.request_context.request
    api_key = request.headers.get("X-API-KEY") if request else None
    if not api_key:
        raise ValueError("API key not found in request headers")
    return api_key


async def request_api(method: str, path: str, api_key: str, **kwargs) -> str:
    """Llama a la API de Lunance inyectando la X-API-Key del usuario y traduce
    los errores HTTP a texto entendible para el modelo."""
    try:
        resp = await _client.request(
            method, path, headers={"X-API-Key": api_key}, **kwargs
        )
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPStatusError as e:
        return f"Error {e.response.status_code}: {e.response.text}"
    except httpx.HTTPError as e:
        return f"No se pudo conectar con la API: {e}"
