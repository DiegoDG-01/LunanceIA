from fastapi import Depends

from application.installments.commands.create_installment_purchase import CreateInstallmentPurchaseHandler
from application.installments.commands.delete_installment_purchase import DeleteInstallmentPurchaseHandler
from application.installments.commands.pay_installment_charge import PayInstallmentChargeHandler
from application.installments.commands.update_installment_purchase import UpdateInstallmentPurchaseHandler
from application.installments.queries.get_installment_purchases import GetInstallmentPurchasesHandler
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.repositories.sqlalchemy_account_repository import SQLAlchemyAccountRepository
from infrastructure.database.repositories.sqlalchemy_installment_charge_repository import SQLAlchemyInstallmentChargeRepository
from infrastructure.database.repositories.sqlalchemy_installment_purchase_repository import SQLAlchemyInstallmentPurchaseRepository
from infrastructure.database.repositories.sqlalchemy_transaction_repository import SQLAlchemyTransactionRepository
from infrastructure.database.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from presentation.dependencies.repositories import (
    get_user_repository,
    get_account_repository,
    get_transaction_repository,
    get_unit_of_work_repository,
    get_installment_purchase_repository,
    get_installment_charge_repository,
)


def get_create_installment_handler(
        user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
        purchase_repo: SQLAlchemyInstallmentPurchaseRepository = Depends(get_installment_purchase_repository),
        charge_repo: SQLAlchemyInstallmentChargeRepository = Depends(get_installment_charge_repository),
        uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> CreateInstallmentPurchaseHandler:
    return CreateInstallmentPurchaseHandler(
        user_repository=user_repo,
        account_repository=account_repo,
        installment_purchase_repository=purchase_repo,
        installment_charge_repository=charge_repo,
        uow=uow,
    )


def get_installment_purchases_handler(
        user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
        purchase_repo: SQLAlchemyInstallmentPurchaseRepository = Depends(get_installment_purchase_repository),
        charge_repo: SQLAlchemyInstallmentChargeRepository = Depends(get_installment_charge_repository),
) -> GetInstallmentPurchasesHandler:
    return GetInstallmentPurchasesHandler(
        user_repository=user_repo,
        account_repository=account_repo,
        installment_purchase_repository=purchase_repo,
        installment_charge_repository=charge_repo,
    )


def get_pay_installment_charge_handler(
        account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
        transaction_repo: SQLAlchemyTransactionRepository = Depends(get_transaction_repository),
        charge_repo: SQLAlchemyInstallmentChargeRepository = Depends(get_installment_charge_repository),
        purchase_repo: SQLAlchemyInstallmentPurchaseRepository = Depends(get_installment_purchase_repository),
        uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> PayInstallmentChargeHandler:
    return PayInstallmentChargeHandler(
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        installment_charge_repository=charge_repo,
        installment_purchase_repository=purchase_repo,
        uow=uow,
    )

def get_delete_installment_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(get_transaction_repository),
    purchase_repo: SQLAlchemyInstallmentPurchaseRepository = Depends(get_installment_purchase_repository),
    charge_repo: SQLAlchemyInstallmentChargeRepository = Depends(get_installment_charge_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> DeleteInstallmentPurchaseHandler:
    return DeleteInstallmentPurchaseHandler(
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        installment_purchase_repository=purchase_repo,
        installment_charge_repository=charge_repo,
        uow=uow,
    )

def get_update_installment_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    purchase_repo: SQLAlchemyInstallmentPurchaseRepository = Depends(get_installment_purchase_repository),
    charge_repo: SQLAlchemyInstallmentChargeRepository = Depends(get_installment_charge_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> UpdateInstallmentPurchaseHandler:
    return UpdateInstallmentPurchaseHandler(
        account_repository=account_repo,
        installment_purchase_repository=purchase_repo,
        installment_charge_repository=charge_repo,
        uow=uow,
    )