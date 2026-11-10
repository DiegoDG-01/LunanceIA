from typing import cast

from fastapi import APIRouter, Depends, Request, Response, status

from application.dto.transaction_dto import CreateTransferDTO
from application.transfers.commands.create_transfer import (
    CreateTransferCommand,
    CreateTransferHandler,
)
from application.transfers.commands.delete_transfer import (
    DeleteTransferCommand,
    DeleteTransferHandler,
)
from domain.entities.users.user import User
from domain.objects.enums import APIKeyScope
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_10_per_minute,
    limiter_20_per_minute,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.dependencies.idempotency_deps import (
    Idempotency,
    accept_idempotency_key,
    require_idempotency_key,
)
from presentation.dependencies.transfer_deps import (
    get_create_transfer_handler,
    get_delete_transfer_handler,
)
from presentation.schemas.requests.transfer import CreateTransferRequest
from presentation.schemas.responses.transfer import TransferResponse

router = APIRouter()


@router.post("/", response_model=TransferResponse, status_code=201)
async def create_transfer(
    request: Request,
    transfer_request: CreateTransferRequest,
    current_user: User = Depends(require_scope(APIKeyScope.TRANSFERS_WRITE.value)),
    handler: CreateTransferHandler = Depends(get_create_transfer_handler),
    idempotency: Idempotency = Depends(require_idempotency_key),
):
    await enforce_rate_limit(limiter_20_per_minute, request)
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

    async def operation():
        result = await handler.handle(command)
        return TransferResponse(**result.__dict__)

    return await idempotency.run(cast(int, current_user.id), operation)


@router.delete("/{transfer_uuid}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transfer(
    request: Request,
    transfer_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.TRANSFERS_WRITE.value)),
    handler: DeleteTransferHandler = Depends(get_delete_transfer_handler),
    idempotency: Idempotency = Depends(accept_idempotency_key),
):
    await enforce_rate_limit(limiter_10_per_minute, request)
    command = DeleteTransferCommand(
        transfer_uuid=transfer_uuid,
        user_id=cast(int, current_user.id),
    )

    async def operation():
        await handler.handle(command)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return await idempotency.run(cast(int, current_user.id), operation)
