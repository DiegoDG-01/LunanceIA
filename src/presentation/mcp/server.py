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


@mcp.tool()
async def list_budgets(
    ctx: Context,
    active_only: bool = False,
    category_id: int | None = None,
) -> str:
    """Lista los presupuestos del usuario, con filtros opcionales por estado
    (solo activos) o categoría. Úsala para responder cuánto tiene presupuestado
    o si tiene un presupuesto para cierta categoría."""
    params = {
        k: v
        for k, v in {"active_only": active_only, "category_id": category_id}.items()
        if v is not None
    }
    return await request_api("GET", "/budgets", get_api_key(ctx), params=params)


@mcp.tool()
async def get_budget(ctx: Context, budget_uuid: str) -> str:
    """Obtiene el detalle de un presupuesto específico por su UUID."""
    try:
        UUID(budget_uuid)
    except ValueError:
        return "El 'budget_uuid' no tiene un formato válido."
    return await request_api("GET", f"/budgets/{budget_uuid}/", get_api_key(ctx))


@mcp.tool()
async def get_budget_progress(ctx: Context, budget_uuid: str) -> str:
    """Obtiene el progreso de un presupuesto en el periodo actual: cuánto se ha
    gastado, cuánto resta, si se disparó la alerta y si se superó el límite."""
    try:
        UUID(budget_uuid)
    except ValueError:
        return "El 'budget_uuid' no tiene un formato válido."
    return await request_api(
        "GET", f"/budgets/{budget_uuid}/progress/", get_api_key(ctx)
    )


@mcp.tool()
async def create_budget(
    ctx: Context,
    name: str,
    limit_amount: float,
    period: str,  # semanal / quincenal / mensual / trimestral / anual
    start_date: str,  # ISO: YYYY-MM-DD
    category_id: int | None = None,
    end_date: str | None = None,  # ISO: YYYY-MM-DD
    alert_percentage: int = 80,
) -> str:
    """Crea un nuevo presupuesto. 'period' debe ser uno de: semanal, quincenal,
    mensual, trimestral, anual. 'limit_amount' es el monto límite (positivo).
    'category_id' es opcional; si se omite el presupuesto aplica a todas las
    categorías. Confirma el resumen con el usuario antes de crear."""
    body = {
        k: v
        for k, v in {
            "name": name,
            "limit_amount": limit_amount,
            "period": period,
            "start_date": start_date,
            "category_id": category_id,
            "end_date": end_date,
            "alert_percentage": alert_percentage,
        }.items()
        if v is not None
    }
    return await request_api("POST", "/budgets", get_api_key(ctx), json=body)


@mcp.tool()
async def list_goals(ctx: Context, active_only: bool = False) -> str:
    """Lista las metas de ahorro del usuario. Úsala para responder qué metas
    tiene, cuánto lleva ahorrado o cuánto le falta."""
    return await request_api(
        "GET", "/goals", get_api_key(ctx), params={"active_only": active_only}
    )


@mcp.tool()
async def get_goal(ctx: Context, goal_uuid: str) -> str:
    """Obtiene el detalle de una meta de ahorro específica por su UUID."""
    try:
        UUID(goal_uuid)
    except ValueError:
        return "El 'goal_uuid' no tiene un formato válido."
    return await request_api("GET", f"/goals/{goal_uuid}/", get_api_key(ctx))


@mcp.tool()
async def create_goal(
    ctx: Context,
    account_uuid: str,
    name: str,
    target_amount: float,
    target_date: str | None = None,  # ISO: YYYY-MM-DD
    description: str | None = None,
) -> str:
    """Crea una nueva meta de ahorro asociada a una cuenta. 'account_uuid'
    identifica la cuenta (usa list_accounts si no lo conoces) y 'target_amount'
    es el monto objetivo (positivo). Confirma el resumen con el usuario antes de crear."""
    body = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "name": name,
            "target_amount": target_amount,
            "target_date": target_date,
            "description": description,
        }.items()
        if v is not None
    }
    return await request_api("POST", "/goals", get_api_key(ctx), json=body)


@mcp.tool()
async def get_investment_yields(
    ctx: Context,
    account_uuid: str,
    limit: int = 365,
    offset: int = 0,
) -> str:
    """Lista los rendimientos históricos (yields) de una cuenta de inversión.
    'account_uuid' identifica la cuenta de inversión."""
    return await request_api(
        "GET",
        f"/investments/{account_uuid}/yields/",
        get_api_key(ctx),
        params={"limit": limit, "offset": offset},
    )


@mcp.tool()
async def get_investment_projections(
    ctx: Context,
    account_uuid: str,
    days: int | None = None,
) -> str:
    """Obtiene la proyección de rendimiento de una cuenta de inversión: balance
    actual, tasa anual, balance final proyectado y proyección diaria. 'days' son
    los días a proyectar; si se omite proyecta hasta el vencimiento (o 365 días)."""
    params = {"days": days} if days is not None else {}
    return await request_api(
        "GET",
        f"/investments/{account_uuid}/projections/",
        get_api_key(ctx),
        params=params,
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
