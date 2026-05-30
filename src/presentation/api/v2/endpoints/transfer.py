from typing import cast

from fastapi import APIRouter, Request, Depends

from application.transfers.commands.create_transfer import (
    CreateTransferHandler,
    CreateTransferCommand,
)
from application.dto.transaction_dto import CreateTransferDTO
from domain.entities.user import User
from presentation.dependencies.auth_deps import get_current_active_user
from presentation.dependencies.transfer_deps import get_create_transfer_handler
from presentation.schemas.requests.transfer import CreateTransferRequest
from presentation.schemas.responses.transfer import TransferResponse
from infrastructure.rate_limiting.limiters import enforce_rate_limit, limiter_20_per_minute

router = APIRouter()


@router.post("/", response_model=TransferResponse, status_code=201)
async def create_transfer(
    request: Request,
    transfer_request: CreateTransferRequest,
    current_user: User = Depends(get_current_active_user),
    handler: CreateTransferHandler = Depends(get_create_transfer_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = CreateTransferDTO(
        user_id=cast(int, current_user.id),
        source_account_uuid=transfer_request.source_account_uuid,
        destination_account_uuid=transfer_request.destination_account_uuid,
        amount=transfer_request.amount,
        description=transfer_request.description,
        notes=transfer_request.notes,
        transfer_date=transfer_request.transfer_date,
    )
    command = CreateTransferCommand(dto=dto)
    result = await handler.handle(command)
    return TransferResponse(**result.__dict__)
