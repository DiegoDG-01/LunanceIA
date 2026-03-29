from fastapi import APIRouter, Request, Depends

from application.banks.queries.get_banks import GetBanksQuery, GetBanksHandler
from presentation.schemas.responses.bank import BankResponse, BankListResponse
from presentation.dependencies.bank_deps import get_banks_handler


from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_10_per_minute,
)

router = APIRouter()


@router.get("/", response_model=BankListResponse)
async def get_banks(
    request: Request,
    only_active: bool = True,
    handler: GetBanksHandler = Depends(get_banks_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    query = GetBanksQuery(only_active=only_active)

    banks = await handler.handle(query)

    return BankListResponse(
        banks=[BankResponse(**bank.__dict__) for bank in banks],
        total=len(banks),
    )
