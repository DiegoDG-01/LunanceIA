from fastapi import APIRouter, Depends, Request
from typing import cast

from application.dto.installment_dto import CreateInstallmentPurchaseDTO
from application.installments.commands.create_installment_purchase import CreateInstallmentPurchaseHandler, \
    CreateInstallmentPurchaseCommand
from application.installments.commands.pay_installment_charge import PayInstallmentChargeHandler, \
    PayInstallmentChargeCommand
from application.installments.queries.get_installment_purchases import GetInstallmentPurchasesHandler, \
    GetInstallmentPurchasesQuery
from presentation.dependencies.installment_deps import (
    get_installment_purchases_handler,
    get_create_installment_handler,
    get_pay_installment_charge_handler
)
from domain.entities.user import User
from infrastructure.rate_limiting.limiters import enforce_rate_limit, limiter_50_per_minute, limiter_20_per_minute
from presentation.dependencies import get_current_active_user
from presentation.schemas.requests.installment import CreateInstallmentPurchaseRequest, PayInstallmentChargeRequest
from presentation.schemas.responses.installment import InstallmentPurchaseResponse, InstallmentChargeResponse

router = APIRouter()


@router.get("/", response_model=list[InstallmentPurchaseResponse])
async def get_installment_purchases(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    handler: GetInstallmentPurchasesHandler = Depends(get_installment_purchases_handler),
):
    enforce_rate_limit(limiter_50_per_minute, request)
    query = GetInstallmentPurchasesQuery(user_id=cast(int, current_user.id))
    result = await handler.handle(query)
    return [InstallmentPurchaseResponse(**r.__dict__) for r in result]


@router.post("/", response_model=InstallmentPurchaseResponse)
async def create_installment_purchase(
    request: Request,
    body: CreateInstallmentPurchaseRequest,
    current_user: User = Depends(get_current_active_user),
    handler: CreateInstallmentPurchaseHandler = Depends(get_create_installment_handler)
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
    return InstallmentPurchaseResponse(**result.__dict__)

@router.post("/{charge_uuid}/pay/", response_model=InstallmentChargeResponse)
async def pay_installment_charge(
    request: Request,
    charge_uuid: str,
    body: PayInstallmentChargeRequest,
    current_user: User = Depends(get_current_active_user),
    handler: PayInstallmentChargeHandler = Depends(get_pay_installment_charge_handler)
):
    enforce_rate_limit(limiter_20_per_minute, request)
    command = PayInstallmentChargeCommand(
        user_id=cast(int, current_user.id),
        charge_uuid=charge_uuid,
        payment_date=body.payment_date
    )
    result = await handler.handle(command)
    return InstallmentChargeResponse(**result.__dict__)