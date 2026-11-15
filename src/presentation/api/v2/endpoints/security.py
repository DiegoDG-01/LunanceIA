"""Valores que cotizan en bolsa (acciones, ETFs, FIBRAs): catálogo y precios de cierre."""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request

from application.securities.queries.get_instrument_prices import (
    GetInstrumentPricesHandler,
    GetInstrumentPricesQuery,
)
from application.securities.queries.search_instruments import (
    SearchInstrumentsHandler,
    SearchInstrumentsQuery,
)
from domain.entities.users.user import User
from domain.objects.enums import APIKeyScope, Market
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_30_per_minute,
    limiter_50_per_minute,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.dependencies.security_deps import (
    get_instrument_prices_handler,
    get_search_instruments_handler,
)
from presentation.schemas.responses.security import (
    InstrumentPriceResponse,
    InstrumentPricesResponse,
    InstrumentResponse,
)
from shared.exceptions.base import ValidationError

router = APIRouter()

MAX_PRICE_RANGE_DAYS = 3660


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
