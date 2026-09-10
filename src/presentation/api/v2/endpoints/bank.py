from fastapi import APIRouter, Depends, Request

from application.banks.queries.get_banks import GetBanksHandler, GetBanksQuery
from domain.entities.user import User
from domain.objects.enums import APIKeyScope
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_10_per_minute,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.dependencies.bank_deps import get_banks_handler
from presentation.schemas.responses.bank import BankListResponse, BankResponse

router = APIRouter()


@router.get("/", response_model=BankListResponse)
async def get_banks(
    request: Request,
    only_active: bool = True,
    current_user: User = Depends(require_scope(APIKeyScope.BANKS_READ.value)),
    handler: GetBanksHandler = Depends(get_banks_handler),
):
    enforce_rate_limit(limiter_10_per_minute, request)
    query = GetBanksQuery(only_active=only_active)

    banks = await handler.handle(query)

    return BankListResponse(
        banks=[BankResponse(**bank.__dict__) for bank in banks],
        total=len(banks),
    )
