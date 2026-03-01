from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from application.banks.queries.get_banks import GetBanksQuery, GetBanksHandler
from presentation.schemas.responses.bank import BankResponse, BankListResponse
from presentation.dependencies.bank_deps import get_banks_handler


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=BankListResponse)
@limiter.limit("10/minute")
async def get_banks(
    request: Request,
    only_active: bool = True,
    handler: GetBanksHandler = Depends(get_banks_handler),
):
    query = GetBanksQuery(only_active=only_active)

    banks = await handler.handle(query)

    return BankListResponse(
        banks=[BankResponse(**bank.__dict__) for bank in banks],
        total=len(banks),
    )
