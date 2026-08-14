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
    try:
        UUID(account_uuid)
    except ValueError:
        return "account_uuid invalid format"

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
    try:
        UUID(account_uuid)
    except ValueError:
        return "account_uuid invalid format"

    params = {"days": days} if days is not None else {}
    return await request_api(
        "GET",
        f"/investments/{account_uuid}/projections/",
        get_api_key(ctx),
        params=params,
    )


@mcp.tool()
async def get_account(ctx: Context, account_uuid: str) -> str:
    """Obtiene el detalle de una cuenta específica por su UUID (saldo, tipo, banco)."""
    try:
        UUID(account_uuid)
    except ValueError:
        return "El 'account_uuid' no tiene un formato válido."
    return await request_api("GET", f"/account/{account_uuid}", get_api_key(ctx))


@mcp.tool()
async def get_account_activity(ctx: Context, account_uuid: str) -> str:
    """Obtiene la actividad reciente (últimos movimientos) de una cuenta por su UUID."""
    try:
        UUID(account_uuid)
    except ValueError:
        return "El 'account_uuid' no tiene un formato válido."
    return await request_api(
        "GET", f"/account/{account_uuid}/activity", get_api_key(ctx)
    )


@mcp.tool()
async def list_banks(ctx: Context, only_active: bool = True) -> str:
    """Lista los bancos disponibles con su 'id'. Úsala para obtener el 'bank_id'
    que necesita create_account."""
    return await request_api(
        "GET", "/bank", get_api_key(ctx), params={"only_active": only_active}
    )


@mcp.tool()
async def create_account(
    ctx: Context,
    bank_id: int,
    name: str,
    account_type: str,  # CHECKING / SAVINGS / CREDIT_CARD / DEBIT_CARD / INVESTMENT / CASH
    initial_balance: float = 0.0,
    currency: str = "MXN",
    # Ajustes de tarjeta de crédito (solo cuando account_type == CREDIT_CARD)
    billing_cycle_day: int | None = None,  # día de facturación 1-31
    payment_due_day: int | None = None,  # día de pago 1-31
    credit_limit: float | None = None,
    minimum_payment_percentage: float | None = None,  # porcentaje 0-100
) -> str:
    """Crea una nueva cuenta del usuario. 'account_type' debe ser uno de:
    CHECKING, SAVINGS, CREDIT_CARD, DEBIT_CARD, INVESTMENT, CASH. 'bank_id' es el
    ID del banco (usa list_banks/list_accounts como referencia).

    INVESTMENT es solo una etiqueta para organizar (plataformas de inversión);
    los rendimientos se configuran creando apartados con create_position en
    cualquier cuenta que no sea de crédito.

    Para tarjetas de crédito (account_type=CREDIT_CARD) puedes incluir los ajustes:
    'billing_cycle_day' (1-31), 'payment_due_day' (1-31), 'credit_limit' y
    'minimum_payment_percentage' (0-100) — se envían juntos y solo aplican a
    CREDIT_CARD. Confirma el resumen con el usuario antes de crear."""
    body: dict = {
        "bank_id": bank_id,
        "name": name,
        "account_type": account_type,
        "initial_balance": initial_balance,
        "currency": currency,
    }

    credit_card_settings = {
        k: v
        for k, v in {
            "billing_cycle_day": billing_cycle_day,
            "payment_due_day": payment_due_day,
            "credit_limit": credit_limit,
            "minimum_payment_percentage": minimum_payment_percentage,
        }.items()
        if v is not None
    }
    if credit_card_settings:
        body["credit_card_settings"] = credit_card_settings

    return await request_api("POST", "/account", get_api_key(ctx), json=body)


@mcp.tool()
async def list_subscriptions(
    ctx: Context,
    account_uuid: str | None = None,
    category_id: int | None = None,
    active_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> str:
    """Lista las suscripciones del usuario (Netflix, Spotify, etc.), con filtros
    opcionales por cuenta, categoría o estado. Úsala para responder qué paga
    recurrentemente o cuánto suma en suscripciones."""
    params = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "category_id": category_id,
            "active_only": active_only,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return await request_api("GET", "/subscription", get_api_key(ctx), params=params)


@mcp.tool()
async def list_subscription_charges(
    ctx: Context, limit: int = 100, offset: int = 0
) -> str:
    """Lista los cargos de suscripciones del usuario con detalle de transacción,
    categoría y cuenta."""
    return await request_api(
        "GET",
        "/subscription/charges/",
        get_api_key(ctx),
        params={"limit": limit, "offset": offset},
    )


@mcp.tool()
async def get_subscription(ctx: Context, subscription_uuid: str) -> str:
    """Obtiene el detalle de una suscripción específica por su UUID."""
    try:
        UUID(subscription_uuid)
    except ValueError:
        return "El 'subscription_uuid' no tiene un formato válido."
    return await request_api(
        "GET", f"/subscription/{subscription_uuid}/", get_api_key(ctx)
    )


@mcp.tool()
async def create_subscription(
    ctx: Context,
    account_uuid: str,
    category_id: int,
    name: str,
    amount: float,
    frequency: str,  # DAILY / WEEKLY / BIWEEKLY / MONTHLY / BIMONTHLY / QUARTERLY / SEMI_ANNUAL / ANNUAL
    start_date: str,  # ISO: YYYY-MM-DD
    end_date: str | None = None,
    billing_day: int | None = None,  # día del mes 1-31
    description: str | None = None,
    service_url: str | None = None,
) -> str:
    """Crea una nueva suscripción recurrente. 'frequency' debe ser uno de: DAILY,
    WEEKLY, BIWEEKLY, MONTHLY, BIMONTHLY, QUARTERLY, SEMI_ANNUAL, ANNUAL. 'amount'
    es el monto por cargo (positivo). Usa list_accounts y list_categories si no
    conoces 'account_uuid' o 'category_id'. Confirma con el usuario antes de crear."""
    body = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "category_id": category_id,
            "name": name,
            "amount": amount,
            "frequency": frequency,
            "start_date": start_date,
            "end_date": end_date,
            "billing_day": billing_day,
            "description": description,
            "service_url": service_url,
        }.items()
        if v is not None
    }
    return await request_api("POST", "/subscription", get_api_key(ctx), json=body)


@mcp.tool()
async def list_installments(ctx: Context) -> str:
    """Lista las compras a plazos / meses sin intereses (MSI) del usuario, con sus
    cargos. Úsala para responder qué compras a plazos tiene y cuánto le resta."""
    return await request_api("GET", "/installments", get_api_key(ctx))


@mcp.tool()
async def create_installment(
    ctx: Context,
    account_uuid: str,
    description: str,
    total_amount: float,
    num_installments: int,  # 2 a 48
    installment_type: str,  # NO_INTEREST / WITH_INTEREST
    purchase_date: str,  # ISO: YYYY-MM-DD
    category_id: int | None = None,
    annual_interest_rate: float = 0.0,
    notes: str | None = None,
) -> str:
    """Crea una compra a plazos. 'installment_type' debe ser 'NO_INTEREST' (MSI) o
    'WITH_INTEREST'. 'num_installments' es el número de meses (2-48). Si es con
    interés, indica 'annual_interest_rate'. Usa list_accounts si no conoces
    'account_uuid'. Confirma con el usuario antes de crear."""
    body = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "category_id": category_id,
            "description": description,
            "total_amount": total_amount,
            "num_installments": num_installments,
            "installment_type": installment_type,
            "annual_interest_rate": annual_interest_rate,
            "purchase_date": purchase_date,
            "notes": notes,
        }.items()
        if v is not None
    }
    return await request_api("POST", "/installments", get_api_key(ctx), json=body)


@mcp.tool()
async def create_transfer(
    ctx: Context,
    source_account_uuid: str,
    destination_account_uuid: str,
    amount: float,
    description: str | None = None,
    notes: str | None = None,
    transfer_date: str | None = None,  # ISO: YYYY-MM-DD
) -> str:
    """Registra una transferencia de dinero entre dos cuentas del usuario. 'amount'
    es positivo. IMPORTANTE: mueve dinero real entre cuentas — muestra siempre un
    resumen (origen, destino, monto) y pide confirmación explícita antes de enviar."""
    body = {
        k: v
        for k, v in {
            "source_account_uuid": source_account_uuid,
            "destination_account_uuid": destination_account_uuid,
            "amount": amount,
            "description": description,
            "notes": notes,
            "transfer_date": transfer_date,
        }.items()
        if v is not None
    }
    return await request_api("POST", "/transfers", get_api_key(ctx), json=body)


@mcp.tool()
async def list_incomes(
    ctx: Context,
    account_uuid: str | None = None,
    category_id: int | None = None,
    active_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> str:
    """Lista los ingresos recurrentes del usuario (nómina, renta, etc.), con
    filtros opcionales por cuenta, categoría o estado. Úsala para responder
    cuánto ingresa recurrentemente o cuándo es su próximo pago."""
    params = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "category_id": category_id,
            "active_only": active_only,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return await request_api("GET", "/incomes", get_api_key(ctx), params=params)


@mcp.tool()
async def create_income(
    ctx: Context,
    account_uuid: str,
    category_id: int,
    name: str,
    amount: float,
    frequency: str,
    start_date: str,
    end_date: str | None = None,
    next_payment_date: str | None = None,
    description: str | None = None,
) -> str:
    """Crea un ingreso recurrente (nómina, renta, pensión). frequency acepta:
    DAILY, WEEKLY, BIWEEKLY, MONTHLY, BIMONTHLY, QUARTERLY, SEMI_ANNUAL,
    ANNUAL. Las fechas van en formato YYYY-MM-DD."""
    body = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "category_id": category_id,
            "name": name,
            "amount": amount,
            "frequency": frequency,
            "start_date": start_date,
            "end_date": end_date,
            "next_payment_date": next_payment_date,
            "description": description,
        }.items()
        if v is not None
    }
    return await request_api("POST", "/incomes", get_api_key(ctx), json=body)


@mcp.tool()
async def get_income_deposits(
    ctx: Context, income_uuid: str, limit: int = 100, offset: int = 0
) -> str:
    """Historial de depósitos generados por un ingreso recurrente (cuándo y
    cuánto se ha depositado)."""
    try:
        UUID(income_uuid)
    except ValueError:
        return "El 'income_uuid' no tiene un formato válido."
    return await request_api(
        "GET",
        f"/incomes/{income_uuid}/deposits/",
        get_api_key(ctx),
        params={"limit": limit, "offset": offset},
    )


def _validate_uuid(value: str, field: str) -> str | None:
    """Devuelve un mensaje de error si el uuid no es válido, None si lo es."""
    try:
        UUID(value)
        return None
    except ValueError:
        return f"El '{field}' no tiene un formato válido."


# ── Transactions ──────────────────────────────────────────────


@mcp.tool()
async def update_transaction(
    ctx: Context,
    transaction_uuid: str,
    description: str | None = None,
    notes: str | None = None,
    category_id: int | None = None,
    transaction_type: str | None = None,
    amount: float | None = None,
    transaction_date: str | None = None,
    account_uuid: str | None = None,
) -> str:
    """Actualiza una transacción existente. Solo envía los campos a cambiar.
    transaction_type acepta INCOME o EXPENSE; fechas en YYYY-MM-DD."""
    if error := _validate_uuid(transaction_uuid, "transaction_uuid"):
        return error
    body = {
        k: v
        for k, v in {
            "description": description,
            "notes": notes,
            "category_id": category_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "transaction_date": transaction_date,
            "account_uuid": account_uuid,
        }.items()
        if v is not None
    }
    return await request_api(
        "PUT", f"/transaction/{transaction_uuid}/", get_api_key(ctx), json=body
    )


@mcp.tool()
async def delete_transaction(ctx: Context, transaction_uuid: str) -> str:
    """Elimina una transacción por su UUID. Esta acción es permanente y
    revierte su efecto en el balance de la cuenta. Pide confirmación explícita
    del usuario antes de ejecutar.
    """
    if error := _validate_uuid(transaction_uuid, "transaction_uuid"):
        return error
    return await request_api(
        "DELETE", f"/transaction/{transaction_uuid}/", get_api_key(ctx)
    )


# ── Accounts ──────────────────────────────────────────────────


@mcp.tool()
async def update_account(
    ctx: Context,
    account_uuid: str,
    name: str | None = None,
    bank_id: int | None = None,
    current_balance: float | None = None,
) -> str:
    """Actualiza una cuenta (nombre, banco o balance). Solo envía los campos
    a cambiar."""
    if error := _validate_uuid(account_uuid, "account_uuid"):
        return error
    body = {
        k: v
        for k, v in {
            "name": name,
            "bank_id": bank_id,
            "current_balance": current_balance,
        }.items()
        if v is not None
    }
    return await request_api(
        "PATCH", f"/account/{account_uuid}/", get_api_key(ctx), json=body
    )


@mcp.tool()
async def set_account_status(ctx: Context, account_uuid: str, is_active: bool) -> str:
    """Activa o desactiva una cuenta."""
    if error := _validate_uuid(account_uuid, "account_uuid"):
        return error
    return await request_api(
        "PATCH",
        f"/account/{account_uuid}/status/",
        get_api_key(ctx),
        json={"is_active": is_active},
    )


@mcp.tool()
async def delete_account(ctx: Context, account_uuid: str) -> str:
    """Elimina una cuenta por su UUID. Esta acción es permanente; falla si la
    cuenta tiene balance o transacciones asociadas. Pide confirmación explícita
    del usuario antes de ejecutar.
    """
    if error := _validate_uuid(account_uuid, "account_uuid"):
        return error
    return await request_api("DELETE", f"/account/{account_uuid}/", get_api_key(ctx))


# ── Budgets ───────────────────────────────────────────────────


@mcp.tool()
async def update_budget(
    ctx: Context,
    budget_uuid: str,
    name: str | None = None,
    limit_amount: float | None = None,
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    alert_percentage: int | None = None,
    category_id: int | None = None,
) -> str:
    """Actualiza un presupuesto. Solo envía los campos a cambiar. period
    acepta: semanal, quincenal, mensual, trimestral, anual."""
    if error := _validate_uuid(budget_uuid, "budget_uuid"):
        return error
    body = {
        k: v
        for k, v in {
            "name": name,
            "limit_amount": limit_amount,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "alert_percentage": alert_percentage,
            "category_id": category_id,
        }.items()
        if v is not None
    }
    return await request_api(
        "PATCH", f"/budgets/{budget_uuid}/", get_api_key(ctx), json=body
    )


@mcp.tool()
async def toggle_budget(ctx: Context, budget_uuid: str) -> str:
    """Pausa o reactiva un presupuesto (invierte su estado actual)."""
    if error := _validate_uuid(budget_uuid, "budget_uuid"):
        return error
    return await request_api(
        "PATCH", f"/budgets/{budget_uuid}/activate/", get_api_key(ctx)
    )


@mcp.tool()
async def delete_budget(ctx: Context, budget_uuid: str) -> str:
    """Elimina un presupuesto por su UUID. Esta acción es permanente. Pide confirmación explícita
    del usuario antes de ejecutar.
    """
    if error := _validate_uuid(budget_uuid, "budget_uuid"):
        return error
    return await request_api("DELETE", f"/budgets/{budget_uuid}/", get_api_key(ctx))


# ── Goals ─────────────────────────────────────────────────────


@mcp.tool()
async def update_goal(
    ctx: Context,
    goal_uuid: str,
    name: str | None = None,
    target_amount: float | None = None,
    target_date: str | None = None,
    description: str | None = None,
) -> str:
    """Actualiza una meta de ahorro. Solo envía los campos a cambiar."""
    if error := _validate_uuid(goal_uuid, "goal_uuid"):
        return error
    body = {
        k: v
        for k, v in {
            "name": name,
            "target_amount": target_amount,
            "target_date": target_date,
            "description": description,
        }.items()
        if v is not None
    }
    return await request_api("PUT", f"/goals/{goal_uuid}/", get_api_key(ctx), json=body)


@mcp.tool()
async def toggle_goal(ctx: Context, goal_uuid: str) -> str:
    """Pausa o reactiva una meta de ahorro (invierte su estado actual)."""
    if error := _validate_uuid(goal_uuid, "goal_uuid"):
        return error
    return await request_api("PATCH", f"/goals/{goal_uuid}/activate/", get_api_key(ctx))


@mcp.tool()
async def delete_goal(ctx: Context, goal_uuid: str) -> str:
    """Elimina una meta de ahorro por su UUID. Esta acción es permanente. Pide confirmación explícita
    del usuario antes de ejecutar.
    """
    if error := _validate_uuid(goal_uuid, "goal_uuid"):
        return error
    return await request_api("DELETE", f"/goals/{goal_uuid}/", get_api_key(ctx))


# ── Subscriptions ─────────────────────────────────────────────


@mcp.tool()
async def update_subscription(
    ctx: Context,
    subscription_uuid: str,
    account_uuid: str,
    name: str | None = None,
    amount: float | None = None,
    frequency: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    billing_day: int | None = None,
    is_active: bool | None = None,
    description: str | None = None,
    service_url: str | None = None,
    category_id: int | None = None,
) -> str:
    """Actualiza una suscripción. account_uuid es obligatorio; el resto solo
    si cambia. frequency acepta: DAILY, WEEKLY, BIWEEKLY, MONTHLY, BIMONTHLY,
    QUARTERLY, SEMI_ANNUAL, ANNUAL."""
    if error := _validate_uuid(subscription_uuid, "subscription_uuid"):
        return error
    body = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "name": name,
            "amount": amount,
            "frequency": frequency,
            "start_date": start_date,
            "end_date": end_date,
            "billing_day": billing_day,
            "is_active": is_active,
            "description": description,
            "service_url": service_url,
            "category_id": category_id,
        }.items()
        if v is not None
    }
    return await request_api(
        "PATCH", f"/subscription/{subscription_uuid}/", get_api_key(ctx), json=body
    )


@mcp.tool()
async def toggle_subscription(ctx: Context, subscription_uuid: str) -> str:
    """Pausa o reactiva una suscripción (invierte su estado actual). Una
    suscripción pausada no genera cargos automáticos."""
    if error := _validate_uuid(subscription_uuid, "subscription_uuid"):
        return error
    return await request_api(
        "PATCH", f"/subscription/{subscription_uuid}/activate/", get_api_key(ctx)
    )


@mcp.tool()
async def delete_subscription(ctx: Context, subscription_uuid: str) -> str:
    """Elimina una suscripción por su UUID. Esta acción es permanente y borra
    su historial de cargos (las transacciones ya generadas se conservan). Pide confirmación explícita
    del usuario antes de ejecutar.
    """
    if error := _validate_uuid(subscription_uuid, "subscription_uuid"):
        return error
    return await request_api(
        "DELETE", f"/subscription/{subscription_uuid}/", get_api_key(ctx)
    )


# ── Recurring incomes ─────────────────────────────────────────


@mcp.tool()
async def update_income(
    ctx: Context,
    income_uuid: str,
    account_uuid: str | None = None,
    name: str | None = None,
    amount: float | None = None,
    frequency: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    next_payment_date: str | None = None,
    is_active: bool | None = None,
    description: str | None = None,
    category_id: int | None = None,
) -> str:
    """Actualiza un ingreso recurrente. Solo envía los campos a cambiar.
    frequency acepta: DAILY, WEEKLY, BIWEEKLY, MONTHLY, BIMONTHLY, QUARTERLY,
    SEMI_ANNUAL, ANNUAL. Fechas en YYYY-MM-DD."""
    if error := _validate_uuid(income_uuid, "income_uuid"):
        return error
    body = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "name": name,
            "amount": amount,
            "frequency": frequency,
            "start_date": start_date,
            "end_date": end_date,
            "next_payment_date": next_payment_date,
            "is_active": is_active,
            "description": description,
            "category_id": category_id,
        }.items()
        if v is not None
    }
    return await request_api(
        "PATCH", f"/incomes/{income_uuid}/", get_api_key(ctx), json=body
    )


@mcp.tool()
async def toggle_income(ctx: Context, income_uuid: str) -> str:
    """Pausa o reactiva un ingreso recurrente (invierte su estado actual). Un
    ingreso pausado no genera depósitos automáticos."""
    if error := _validate_uuid(income_uuid, "income_uuid"):
        return error
    return await request_api(
        "PATCH", f"/incomes/{income_uuid}/activate/", get_api_key(ctx)
    )


@mcp.tool()
async def delete_income(ctx: Context, income_uuid: str) -> str:
    """Elimina un ingreso recurrente por su UUID. Esta acción es permanente y
    borra su historial de depósitos (las transacciones generadas se
    conservan). Pide confirmación explícita
    del usuario antes de ejecutar.
    """
    if error := _validate_uuid(income_uuid, "income_uuid"):
        return error
    return await request_api("DELETE", f"/incomes/{income_uuid}/", get_api_key(ctx))


# ── Installments ──────────────────────────────────────────────


@mcp.tool()
async def update_installment(
    ctx: Context,
    purchase_uuid: str,
    description: str | None = None,
    notes: str | None = None,
    category_id: int | None = None,
) -> str:
    """Actualiza la descripción, notas o categoría de una compra a meses."""
    if error := _validate_uuid(purchase_uuid, "purchase_uuid"):
        return error
    body = {
        k: v
        for k, v in {
            "description": description,
            "notes": notes,
            "category_id": category_id,
        }.items()
        if v is not None
    }
    return await request_api(
        "PATCH", f"/installments/{purchase_uuid}/", get_api_key(ctx), json=body
    )


@mcp.tool()
async def pay_installment_charge(
    ctx: Context, charge_uuid: str, payment_date: str
) -> str:
    """Paga una cuota específica de una compra a meses. Crea la transacción y
    descuenta el balance de la cuenta. payment_date en YYYY-MM-DD."""
    if error := _validate_uuid(charge_uuid, "charge_uuid"):
        return error
    return await request_api(
        "POST",
        f"/installments/{charge_uuid}/pay/",
        get_api_key(ctx),
        json={"payment_date": payment_date},
    )


@mcp.tool()
async def delete_installment(ctx: Context, purchase_uuid: str) -> str:
    """Elimina una compra a meses por su UUID. Esta acción es permanente. Pide confirmación explícita
    del usuario antes de ejecutar.
    """
    if error := _validate_uuid(purchase_uuid, "purchase_uuid"):
        return error
    return await request_api(
        "DELETE", f"/installments/{purchase_uuid}/", get_api_key(ctx)
    )


# ── Transfers ─────────────────────────────────────────────────


@mcp.tool()
async def delete_transfer(ctx: Context, transfer_uuid: str) -> str:
    """Elimina una transferencia por su UUID y revierte los balances de las
    cuentas involucradas. Esta acción es permanente. Pide confirmación explícita
    del usuario antes de ejecutar.
    """
    if error := _validate_uuid(transfer_uuid, "transfer_uuid"):
        return error
    return await request_api("DELETE", f"/transfers/{transfer_uuid}/", get_api_key(ctx))


# ── Investment positions (apartados) ──────────────────────────


@mcp.tool()
async def list_positions(
    ctx: Context, account_uuid: str, include_liquidated: bool = False
) -> str:
    """Lista los apartados de inversión de una cuenta con sus saldos y el
    resumen de la cuenta: saldo disponible, invertido y total. Úsala para
    responder cuánto tiene apartado/invertido el usuario y en qué."""
    if error := _validate_uuid(account_uuid, "account_uuid"):
        return error
    return await request_api(
        "GET",
        f"/positions/account/{account_uuid}/",
        get_api_key(ctx),
        params={"include_liquidated": include_liquidated},
    )


@mcp.tool()
async def get_position(ctx: Context, position_uuid: str) -> str:
    """Obtiene el detalle de un apartado de inversión por su UUID: capital,
    rendimiento acumulado, tasa, plazo y estado."""
    if error := _validate_uuid(position_uuid, "position_uuid"):
        return error
    return await request_api("GET", f"/positions/{position_uuid}/", get_api_key(ctx))


@mcp.tool()
async def create_position(
    ctx: Context,
    account_uuid: str,
    name: str,
    position_type: str,  # ON_DEMAND (a la vista) / FIXED_TERM (plazo fijo)
    amount: float,
    annual_rate: float,
    interest_type: str = "COMPOUND",  # SIMPLE / COMPOUND
    term_days: int | None = None,
    maturity_date: str | None = None,  # ISO: YYYY-MM-DD (alternativa a term_days)
    lock_period_end_date: str | None = None,  # ISO: YYYY-MM-DD
    early_withdrawal_penalty: float | None = None,  # % 0-100 sobre rendimientos
    on_maturity: str = "HOLD",  # AUTO_RENEW / LIQUIDATE / HOLD
) -> str:
    """Crea un apartado de inversión dentro de una cuenta, moviendo 'amount'
    del saldo disponible al apartado. 'position_type' es ON_DEMAND (a la vista,
    admite depósitos/retiros) o FIXED_TERM (plazo fijo: requiere 'term_days' o
    'maturity_date' y no admite movimientos hasta vencer). 'on_maturity' define
    qué pasa al vencer un plazo: AUTO_RENEW (reinvierte), LIQUIDATE (regresa al
    disponible) o HOLD (espera decisión del usuario). El dinero apartado NO se
    puede gastar ni transferir hasta retirarlo al disponible. IMPORTANTE: mueve
    dinero real — muestra un resumen y pide confirmación explícita antes de crear."""
    if error := _validate_uuid(account_uuid, "account_uuid"):
        return error
    body = {
        k: v
        for k, v in {
            "account_uuid": account_uuid,
            "name": name,
            "position_type": position_type,
            "amount": amount,
            "annual_rate": annual_rate,
            "interest_type": interest_type,
            "term_days": term_days,
            "maturity_date": maturity_date,
            "lock_period_end_date": lock_period_end_date,
            "early_withdrawal_penalty": early_withdrawal_penalty,
            "on_maturity": on_maturity,
        }.items()
        if v is not None
    }
    return await request_api("POST", "/positions", get_api_key(ctx), json=body)


@mcp.tool()
async def deposit_to_position(ctx: Context, position_uuid: str, amount: float) -> str:
    """Mueve dinero del saldo disponible de la cuenta hacia un apartado a la
    vista (los plazos fijos no admiten depósitos). IMPORTANTE: mueve dinero
    real — pide confirmación explícita del usuario antes de ejecutar."""
    if error := _validate_uuid(position_uuid, "position_uuid"):
        return error
    return await request_api(
        "POST",
        f"/positions/{position_uuid}/deposit/",
        get_api_key(ctx),
        json={"amount": amount},
    )


@mcp.tool()
async def withdraw_from_position(
    ctx: Context, position_uuid: str, amount: float
) -> str:
    """Regresa dinero de un apartado a la vista al saldo disponible de la
    cuenta. Es el único camino para poder gastar o transferir dinero apartado
    (los plazos fijos solo se liquidan por completo). IMPORTANTE: mueve dinero
    real — pide confirmación explícita del usuario antes de ejecutar."""
    if error := _validate_uuid(position_uuid, "position_uuid"):
        return error
    return await request_api(
        "POST",
        f"/positions/{position_uuid}/withdraw/",
        get_api_key(ctx),
        json={"amount": amount},
    )


@mcp.tool()
async def liquidate_position(ctx: Context, position_uuid: str) -> str:
    """Cierra un apartado por completo y regresa capital + rendimiento al saldo
    disponible. Liquidar un plazo fijo antes de su vencimiento aplica la
    penalización configurada sobre los rendimientos, y no se permite durante el
    periodo de permanencia. IMPORTANTE: acción permanente que mueve dinero
    real — muestra el detalle y pide confirmación explícita antes de ejecutar."""
    if error := _validate_uuid(position_uuid, "position_uuid"):
        return error
    return await request_api(
        "POST", f"/positions/{position_uuid}/liquidate/", get_api_key(ctx)
    )


@mcp.tool()
async def get_position_yields(
    ctx: Context, position_uuid: str, limit: int = 365, offset: int = 0
) -> str:
    """Lista los rendimientos diarios históricos de un apartado de inversión."""
    if error := _validate_uuid(position_uuid, "position_uuid"):
        return error
    return await request_api(
        "GET",
        f"/positions/{position_uuid}/yields/",
        get_api_key(ctx),
        params={"limit": limit, "offset": offset},
    )


@mcp.tool()
async def get_position_projections(
    ctx: Context, position_uuid: str, days: int | None = None
) -> str:
    """Proyección de rendimiento de un apartado: valor actual, tasa y balance
    proyectado día a día. 'days' son los días a proyectar; si se omite proyecta
    hasta el vencimiento (o 365 días para apartados a la vista)."""
    if error := _validate_uuid(position_uuid, "position_uuid"):
        return error
    params = {"days": days} if days is not None else {}
    return await request_api(
        "GET",
        f"/positions/{position_uuid}/projections/",
        get_api_key(ctx),
        params=params,
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
