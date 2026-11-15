"""Valores que cotizan en bolsa (acciones, ETFs, FIBRAs): catálogo y precios de cierre."""

from datetime import UTC, date, datetime, timedelta
from typing import cast

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from application.securities.commands.delete_trade import (
    DeleteTradeCommand,
    DeleteTradeHandler,
)
from application.securities.commands.record_trade import (
    RecordTradeCommand,
    RecordTradeHandler,
)
from application.securities.commands.update_trade import (
    UpdateTradeCommand,
    UpdateTradeHandler,
)
from application.securities.dto import TradeResultDTO
from application.securities.queries.get_instrument_prices import (
    GetInstrumentPricesHandler,
    GetInstrumentPricesQuery,
)
from application.securities.queries.list_holdings import (
    GetHoldingQuery,
    HoldingHistoryQuery,
    HoldingQueries,
    ListHoldingsQuery,
)
from application.securities.queries.list_trades import (
    ListTradesHandler,
    ListTradesQuery,
)
from application.securities.queries.portfolio import PortfolioQueries
from application.securities.queries.search_instruments import (
    SearchInstrumentsHandler,
    SearchInstrumentsQuery,
)
from domain.entities.users.user import User
from domain.objects.enums import APIKeyScope, Market
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_20_per_minute,
    limiter_30_per_minute,
    limiter_50_per_minute,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.dependencies.idempotency_deps import (
    Idempotency,
    accept_idempotency_key,
    require_idempotency_key,
)
from presentation.dependencies.security_deps import (
    InstrumentTracker,
    get_delete_trade_handler,
    get_holding_queries,
    get_instrument_prices_handler,
    get_instrument_tracker,
    get_list_trades_handler,
    get_portfolio_queries,
    get_record_trade_handler,
    get_search_instruments_handler,
    get_update_trade_handler,
)
from presentation.schemas.requests.security import (
    CreateTradeRequest,
    UpdateTradeRequest,
)
from presentation.schemas.responses.security import (
    HoldingDetailResponse,
    HoldingHistoryResponse,
    HoldingResponse,
    HoldingSnapshotResponse,
    InstrumentPriceResponse,
    InstrumentPricesResponse,
    InstrumentResponse,
    PortfolioDayResponse,
    PortfolioHistoryResponse,
    PortfolioSummaryResponse,
    TradeResponse,
    TradeResultResponse,
)
from shared.exceptions.base import ValidationError

router = APIRouter()

MAX_PRICE_RANGE_DAYS = 3660


def _date_range(from_date: date | None, to_date: date | None) -> tuple[date, date]:
    """Rango de una consulta de historia: por defecto, los últimos 365 días."""
    end = to_date or datetime.now(UTC).date()
    start = from_date or end - timedelta(days=365)
    if start > end:
        raise ValidationError("'from' no puede ser posterior a 'to'")
    if (end - start).days > MAX_PRICE_RANGE_DAYS:
        raise ValidationError(f"El rango máximo es de {MAX_PRICE_RANGE_DAYS} días")
    return start, end


@router.get("/search", response_model=list[InstrumentResponse])
async def search_instruments(
    request: Request,
    q: str = Query(..., min_length=1, max_length=60, description="Símbolo o nombre"),
    market: Market | None = Query(None, description="BMV, SIC o US"),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    handler: SearchInstrumentsHandler = Depends(get_search_instruments_handler),
):
    """Busca en el catálogo. BMV/BIVA y SIC están completos; para EE. UU., un símbolo que no
    está se consulta al proveedor y se agrega."""
    await enforce_rate_limit(limiter_30_per_minute, request)
    instruments = await handler.handle(
        SearchInstrumentsQuery(query=q, market=market, limit=limit)
    )
    return [InstrumentResponse.from_entity(i) for i in instruments]


@router.get(
    "/instruments/{instrument_uuid}/prices", response_model=InstrumentPricesResponse
)
async def get_instrument_prices(
    request: Request,
    instrument_uuid: str,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    handler: GetInstrumentPricesHandler = Depends(get_instrument_prices_handler),
):
    """Cierres diarios guardados (sin ajustar, en la moneda del valor). Por defecto, los
    últimos 30 días. Solo hay precios de los valores que alguien sigue."""
    await enforce_rate_limit(limiter_50_per_minute, request)
    end = to_date or datetime.now(UTC).date()
    start = from_date or end - timedelta(days=30)
    if start > end:
        raise ValidationError("'from' no puede ser posterior a 'to'")
    if (end - start).days > MAX_PRICE_RANGE_DAYS:
        raise ValidationError(f"El rango máximo es de {MAX_PRICE_RANGE_DAYS} días")
    result = await handler.handle(
        GetInstrumentPricesQuery(instrument_uuid=instrument_uuid, start=start, end=end)
    )
    return InstrumentPricesResponse(
        instrument=InstrumentResponse.from_entity(result.instrument),
        prices=[InstrumentPriceResponse.from_entity(p) for p in result.prices],
    )


def _track(
    background: BackgroundTasks, tracker: InstrumentTracker, result: TradeResultDTO
) -> None:
    if result.trade is not None:
        background.add_task(
            tracker, cast(int, result.trade.instrument.id), result.trade.trade_date
        )


@router.post("/trades/", response_model=TradeResultResponse, status_code=201)
async def record_trade(
    request: Request,
    body: CreateTradeRequest,
    background: BackgroundTasks,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_WRITE.value)),
    handler: RecordTradeHandler = Depends(get_record_trade_handler),
    tracker: InstrumentTracker = Depends(get_instrument_tracker),
    idempotency: Idempotency = Depends(require_idempotency_key),
):
    """Registra una compra, venta, dividendo o split. Compra y venta mueven el disponible
    de la cuenta (transacción TRANSFER); el dividendo entra como ingreso en «Inversiones».
    La primera operación de un valor descarga su historia de precios en segundo plano."""
    await enforce_rate_limit(limiter_20_per_minute, request)
    command = RecordTradeCommand(
        user_id=cast(int, current_user.id),
        account_uuid=body.account_uuid,
        instrument_uuid=body.instrument_uuid,
        trade_type=body.trade_type,
        trade_date=body.trade_date,
        quantity=body.quantity,
        price=body.price,
        fees=body.fees,
        tax_withheld=body.tax_withheld,
        gross_amount=body.gross_amount,
        split_from=body.split_from,
        split_to=body.split_to,
        notes=body.notes,
    )

    async def operation():
        result = await handler.handle(command)
        _track(background, tracker, result)
        return TradeResultResponse.from_dto(result)

    return await idempotency.run(cast(int, current_user.id), operation)


@router.get("/trades/", response_model=list[TradeResponse])
async def list_trades(
    request: Request,
    account_uuid: str | None = Query(None),
    instrument_uuid: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    handler: ListTradesHandler = Depends(get_list_trades_handler),
):
    """Operaciones del usuario, las más recientes primero."""
    await enforce_rate_limit(limiter_50_per_minute, request)
    trades = await handler.handle(
        ListTradesQuery(
            user_id=cast(int, current_user.id),
            account_uuid=account_uuid,
            instrument_uuid=instrument_uuid,
            limit=limit,
            offset=offset,
        )
    )
    return [TradeResponse.from_dto(t) for t in trades]


@router.put("/trades/{trade_uuid}", response_model=TradeResultResponse)
async def update_trade(
    request: Request,
    trade_uuid: str,
    body: UpdateTradeRequest,
    background: BackgroundTasks,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_WRITE.value)),
    handler: UpdateTradeHandler = Depends(get_update_trade_handler),
    tracker: InstrumentTracker = Depends(get_instrument_tracker),
    idempotency: Idempotency = Depends(accept_idempotency_key),
):
    """Reemplaza los datos de una operación y recalcula la tenencia. Se rechaza si deja una
    venta posterior sin títulos."""
    await enforce_rate_limit(limiter_20_per_minute, request)
    command = UpdateTradeCommand(
        user_id=cast(int, current_user.id),
        trade_uuid=trade_uuid,
        trade_date=body.trade_date,
        quantity=body.quantity,
        price=body.price,
        fees=body.fees,
        tax_withheld=body.tax_withheld,
        gross_amount=body.gross_amount,
        split_from=body.split_from,
        split_to=body.split_to,
        notes=body.notes,
    )

    async def operation():
        result = await handler.handle(command)
        _track(background, tracker, result)
        return TradeResultResponse.from_dto(result)

    return await idempotency.run(cast(int, current_user.id), operation)


@router.delete("/trades/{trade_uuid}", response_model=TradeResultResponse)
async def delete_trade(
    request: Request,
    trade_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_WRITE.value)),
    handler: DeleteTradeHandler = Depends(get_delete_trade_handler),
    idempotency: Idempotency = Depends(accept_idempotency_key),
):
    """Borra una operación y revierte su movimiento de dinero. Se rechaza si deja una venta
    posterior sin títulos."""
    await enforce_rate_limit(limiter_20_per_minute, request)

    async def operation():
        result = await handler.handle(
            DeleteTradeCommand(
                user_id=cast(int, current_user.id), trade_uuid=trade_uuid
            )
        )
        return TradeResultResponse.from_dto(result)

    return await idempotency.run(cast(int, current_user.id), operation)


@router.get("/holdings/", response_model=list[HoldingResponse])
async def list_holdings(
    request: Request,
    account_uuid: str | None = Query(None),
    include_closed: bool = Query(False),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    queries: HoldingQueries = Depends(get_holding_queries),
):
    """Lo que hay de cada valor, con su valor al último cierre guardado."""
    await enforce_rate_limit(limiter_50_per_minute, request)
    holdings = await queries.list_holdings(
        ListHoldingsQuery(
            user_id=cast(int, current_user.id),
            account_uuid=account_uuid,
            include_closed=include_closed,
        )
    )
    return [HoldingResponse.from_dto(h) for h in holdings]


@router.get("/holdings/{holding_uuid}", response_model=HoldingDetailResponse)
async def get_holding(
    request: Request,
    holding_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    queries: HoldingQueries = Depends(get_holding_queries),
):
    await enforce_rate_limit(limiter_50_per_minute, request)
    detail = await queries.get_holding(
        GetHoldingQuery(user_id=cast(int, current_user.id), holding_uuid=holding_uuid)
    )
    return HoldingDetailResponse(
        holding=HoldingResponse.from_dto(detail.holding),
        trades=[TradeResponse.from_dto(t) for t in detail.trades],
    )


@router.get("/holdings/{holding_uuid}/history", response_model=HoldingHistoryResponse)
async def get_holding_history(
    request: Request,
    holding_uuid: str,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    queries: HoldingQueries = Depends(get_holding_queries),
):
    """Fotos diarias de la tenencia: cantidad, valor, costo y ganancias de cada día de
    calendario. Por defecto, los últimos 365 días."""
    await enforce_rate_limit(limiter_50_per_minute, request)
    start, end = _date_range(from_date, to_date)
    history = await queries.history(
        HoldingHistoryQuery(
            user_id=cast(int, current_user.id),
            holding_uuid=holding_uuid,
            start=start,
            end=end,
        )
    )
    return HoldingHistoryResponse(
        holding=HoldingResponse.from_dto(history.holding),
        snapshots=[HoldingSnapshotResponse.from_entity(s) for s in history.snapshots],
    )


@router.get("/portfolio/", response_model=PortfolioSummaryResponse)
async def get_portfolio(
    request: Request,
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    queries: PortfolioQueries = Depends(get_portfolio_queries),
):
    """Patrimonio en pesos: disponible de las cuentas, tarjetas de crédito, apartados y
    acciones al último cierre. `missing` dice qué no se pudo sumar."""
    await enforce_rate_limit(limiter_50_per_minute, request)
    summary = await queries.summary(cast(int, current_user.id))
    return PortfolioSummaryResponse.from_summary(summary)


@router.get("/portfolio/history", response_model=PortfolioHistoryResponse)
async def get_portfolio_history(
    request: Request,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    current_user: User = Depends(require_scope(APIKeyScope.INVESTMENTS_READ.value)),
    queries: PortfolioQueries = Depends(get_portfolio_queries),
):
    """Lo invertido por día en pesos: apartados más acciones. Por defecto, los últimos
    365 días; no incluye días anteriores a la primera inversión."""
    await enforce_rate_limit(limiter_50_per_minute, request)
    start, end = _date_range(from_date, to_date)
    days = await queries.history(cast(int, current_user.id), start, end)
    return PortfolioHistoryResponse(
        start=start, end=end, days=[PortfolioDayResponse.from_day(d) for d in days]
    )
