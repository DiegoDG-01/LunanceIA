from domain.services.account_service import AccountService


def get_account_service() -> AccountService:
    return AccountService()
