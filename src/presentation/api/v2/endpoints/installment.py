from fastapi import APIRouter, Depends, Request
from typing import cast

from application.dto.installment_dto import CreateInstallmentPurchaseDTO
from application.installments.commands.create_installment_purchase import (
    CreateInstallmentPurchaseHandler,
    CreateInstallmentPurchaseCommand,
)
from application.installments.commands.delete_installment_purchase import (
    DeleteInstallmentPurchaseHandler,
    DeleteInstallmentPurchaseCommand,
)
from application.installments.commands.pay_installment_charge import (
    PayInstallmentChargeHandler,
    PayInstallmentChargeCommand,
)
from application.installments.commands.update_installment_purchase import (
    UpdateInstallmentPurchaseHandler,
    UpdateInstallmentPurchaseCommand,
)
from application.installments.queries.get_installment_purchases import (
    GetInstallmentPurchasesHandler,
    GetInstallmentPurchasesQuery,
)
from presentation.dependencies.installment_deps import (
    get_installment_purchases_handler,
    get_create_installment_handler,
    get_pay_installment_charge_handler,
    get_delete_installment_handler,
    get_update_installment_handler,
)
from domain.entities.user import User
from domain.objects.enums import APIKeyScope
from infrastructure.rate_limiting.limiters import (
    enforce_rate_limit,
    limiter_50_per_minute,
    limiter_20_per_minute,
)
from presentation.dependencies.auth_deps import require_scope
from presentation.schemas.requests.installment import (
    CreateInstallmentPurchaseRequest,
    PayInstallmentChargeRequest,
    UpdateInstallmentPurchaseRequest,
)
from presentation.schemas.responses.installment import (
    InstallmentPurchaseResponse,
    InstallmentChargeResponse,
)

router = APIRouter()


@router.get("/", response_model=list[InstallmentPurchaseResponse])
async def get_installment_purchases(
    request: Request,
    current_user: User = Depends(require_scope(APIKeyScope.INSTALLMENTS_READ.value)),
    handler: GetInstallmentPurchasesHandler = Depends(
        get_installment_purchases_handler
    ),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetInstallmentPurchasesQuery(user_id=cast(int, current_user.id))
    result = await handler.handle(query)
    return [
        InstallmentPurchaseResponse(
            **{
                **r.__dict__,
                "charges": [InstallmentChargeResponse(**c.__dict__) for c in r.charges],
            }
        )
        for r in result
    ]


@router.post("/", response_model=InstallmentPurchaseResponse)
async def create_installment_purchase(
    request: Request,
    body: CreateInstallmentPurchaseRequest,
    current_user: User = Depends(require_scope(APIKeyScope.INSTALLMENTS_WRITE.value)),
    handler: CreateInstallmentPurchaseHandler = Depends(get_create_installment_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    dto = CreateInstallmentPurchaseDTO(
        user_id=cast(int, current_user.id),
        account_uuid=body.account_uuid,
        category_id=body.category_id,
        description=body.description,
        total_amount=body.total_amount,
        num_installments=body.num_installments,
        installment_type=body.installment_type,
        annual_interest_rate=body.annual_interest_rate,
        purchase_date=body.purchase_date,
        notes=body.notes,
    )
    result = await handler.handle(CreateInstallmentPurchaseCommand(dto=dto))
    charges = [InstallmentChargeResponse(**c.__dict__) for c in result.charges]
    return InstallmentPurchaseResponse(**{**result.__dict__, "charges": charges})


@router.post("/{charge_uuid}/pay/", response_model=InstallmentChargeResponse)
async def pay_installment_charge(
    request: Request,
    charge_uuid: str,
    body: PayInstallmentChargeRequest,
    current_user: User = Depends(require_scope(APIKeyScope.INSTALLMENTS_WRITE.value)),
    handler: PayInstallmentChargeHandler = Depends(get_pay_installment_charge_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    command = PayInstallmentChargeCommand(
        user_id=cast(int, current_user.id),
        charge_uuid=charge_uuid,
        payment_date=body.payment_date,
    )
    result = await handler.handle(command)
    return InstallmentChargeResponse(**result.__dict__)


@router.delete("/{purchase_uuid}/", status_code=204)
async def delete_installment_purchase(
    request: Request,
    purchase_uuid: str,
    current_user: User = Depends(require_scope(APIKeyScope.INSTALLMENTS_WRITE.value)),
    handler: DeleteInstallmentPurchaseHandler = Depends(get_delete_installment_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    command = DeleteInstallmentPurchaseCommand(
        user_id=cast(int, current_user.id), purchase_uuid=purchase_uuid
    )
    await handler.handle(command)


@router.patch("/{purchase_uuid}/", response_model=InstallmentPurchaseResponse)
async def update_installment_purchase(
    request: Request,
    purchase_uuid: str,
    body: UpdateInstallmentPurchaseRequest,
    current_user: User = Depends(require_scope(APIKeyScope.INSTALLMENTS_WRITE.value)),
    handler: UpdateInstallmentPurchaseHandler = Depends(get_update_installment_handler),
):
    enforce_rate_limit(limiter_20_per_minute, request)
    command = UpdateInstallmentPurchaseCommand(
        user_id=cast(int, current_user.id),
        purchase_uuid=purchase_uuid,
        description=body.description,
        notes=body.notes,
        category_id=body.category_id,
    )
    result = await handler.handle(command)
    charges = [InstallmentChargeResponse(**c.__dict__) for c in result.charges]
    return InstallmentPurchaseResponse(**{**result.__dict__, "charges": charges})
