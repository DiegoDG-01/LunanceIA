from domain.entities.account import Account
from domain.entities.transaction import Transaction
from domain.objects.money import Money
from domain.objects.enums import TransactionType


class AccountService:
    """
    Service to manage accounts
    """
    def calculate_balance_after_transaction(self, account: Account, transaction: Transaction) -> Money:
        """
        Calculate the balance after a transaction
        """
        current_balance = account.current_balance
        if transaction.is_income():
            return current_balance.add(transaction.amount)
        else:
            return current_balance.subtract(transaction.amount)


    def can_process_transaction(self, account: Account, transaction: Transaction) -> bool:
        """
        Check if a transaction can be processed
        """
        if not account.is_active:
            return False
        if transaction.is_expense():
            return account.can_withdraw(transaction.amount)
        return True

    def validate_account_for_deletion(self, account: Account, transactions: list[Transaction]) -> bool:
        """
        Check if an account can be deleted
        """
        return account.current_balance.amount == 0
