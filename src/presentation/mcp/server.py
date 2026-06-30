from uuid import UUID

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.transport_security import TransportSecuritySettings

from presentation.mcp.client import get_api_key, request_api
from presentation.mcp.config import mcp_settings

mcp = FastMCP(
    name="Lunance",
    host=mcp_settings.MCP_HOST,
    port=mcp_settings.MCP_PORT,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=mcp_settings.allowed_hosts,
        allowed_origins=mcp_settings.allowed_origins,
    ),
)


@mcp.tool()
async def list_transactions(
    ctx: Context,
    skip: int = 0,
    limit: int = 100,
    start_date: str | None = None,  # ISO: YYYY-MM-DD
    end_date: str | None = None,
    transaction_type: str | None = None,  # INCOME / EXPENSE
    category_id: int | None = None,
    account_uuid: str | None = None,
) -> str:
    """Lista las transacciones (gastos e ingresos) del usuario, con filtros
    opcionales por fecha, tipo, categoría o cuenta. Úsala para responder
    cuánto se ha gastado, movimientos recientes, etc."""
    params = {
        k: v
        for k, v in {
            "skip": skip,
            "limit": limit,
            "start_date": start_date,
            "end_date": end_date,
            "transaction_type": transaction_type,
            "category_id": category_id,
            "account_uuid": account_uuid,
        }.items()
        if v is not None
    }
    return await request_api("GET", "/transaction", get_api_key(ctx), params=params)


@mcp.tool()
async def get_transaction(ctx: Context, transaction_uuid: str) -> str:
    """Obtiene el detalle de una transacción específica por su UUID."""
    try:
        UUID(transaction_uuid)
    except ValueError:
        return "El 'transaction_uuid' no tiene un formato válido."
    return await request_api(
        "GET", f"/transaction/{transaction_uuid}/", get_api_key(ctx)
    )


@mcp.tool()
async def create_transaction(
    ctx: Context,
    account_uuid: str,
    transaction_type: str,  # INCOME / EXPENSE
    amount: float,
    category_id: int | None = None,
    description: str | None = None,
    notes: str | None = None,
    transaction_date: str | None = None,  # ISO: YYYY-MM-DD
) -> str:
    """Registra una nueva transacción (gasto o ingreso) en una cuenta del usuario.
    'transaction_type' debe ser 'INCOME' o 'EXPENSE' y 'amount' debe ser positivo.
    'account_uuid' identifica la cuenta; usa list_accounts si no lo conoces."""
    body = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "transaction_type": transaction_type,
            "amount": amount,
            "category_id": category_id,
            "description": description,
            "notes": notes,
            "transaction_date": transaction_date,
        }.items()
        if v is not None
    }
    return await request_api("POST", "/transaction", get_api_key(ctx), json=body)


@mcp.tool()
async def get_dashboard(ctx: Context) -> str:
    """Obtiene el resumen financiero del usuario (dashboard): balances,
    ingresos/gastos del periodo y métricas generales."""
    return await request_api("GET", "/dashboard", get_api_key(ctx))


@mcp.tool()
async def list_categories(ctx: Context, only_active: bool = True) -> str:
    """Lista las categorías disponibles para clasificar transacciones."""
    return await request_api(
        "GET", "/category", get_api_key(ctx), params={"only_active": only_active}
    )


@mcp.tool()
async def list_accounts(ctx: Context, limit: int = 50, offset: int = 0) -> str:
    """Lista las cuentas del usuario (bancos, efectivo, etc.) con sus saldos."""
    return await request_api(
        "GET", "/account", get_api_key(ctx), params={"limit": limit, "offset": offset}
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
