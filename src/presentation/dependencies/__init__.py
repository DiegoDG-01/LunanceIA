# Re-export all dependencies for backwards compatibility
# Repositories
from presentation.dependencies.repositories import (
    get_account_repository,
    get_user_repository,
    get_transaction_repository,
    get_category_repository,
    get_subscription_repository,
    get_subscription_charge_repository,
    get_credit_card_settings_repository,
    get_investment_settings_repository,
    get_auth_token_repository,
    get_dashboard_repository,
)

# Services
from presentation.dependencies.services import (
    get_account_service,
    get_jwt_service,
)

# Account handlers
from presentation.dependencies.account_deps import (
    get_create_account_handler,
    get_update_account_handler,
    get_delete_account_handler,
    get_state_account_handler,
    get_user_accounts_handler,
    get_account_by_id_handler,
    get_activity_account_handler,
)

# Transaction handlers
from presentation.dependencies.transaction_deps import (
    get_transactions_handler,
    get_transaction_by_uuid_handler,
    get_create_transaction_handler,
    get_update_transaction_handler,
    get_delete_transaction_handler,
)

# Subscription handlers
from presentation.dependencies.subscription_deps import (
    get_create_subscription_handler,
    get_update_subscription_handler,
    get_state_subscription_handler,
    get_subscriptions_handler,
    get_subscription_by_id_handler,
    get_subscription_charges_handler,
    get_delete_subscription_handler,
    get_last_transactions_handler,
)

# Category handlers
from presentation.dependencies.category_deps import get_categories_handler

# Dashboard handlers
from presentation.dependencies.dashboard_deps import get_dashboard_summary_handler

# Auth handlers
from presentation.dependencies.auth_handler_deps import (
    get_login_handler,
    get_register_handler,
    get_refresh_token_handler,
    get_logout_handler,
)

# Auth (JWT validation, current user)
from presentation.dependencies.auth_deps import (
    get_current_user,
    get_current_active_user,
    validate_token,
)

# Bank Handlers
from .bank_deps import get_banks_handler

# AI Handlers
from .ai_deps import get_analyze_image_handler, get_expense_advisor_handler


__all__ = [
    # Repositories
    "get_account_repository",
    "get_user_repository",
    "get_transaction_repository",
    "get_category_repository",
    "get_subscription_repository",
    "get_subscription_charge_repository",
    "get_credit_card_settings_repository",
    "get_investment_settings_repository",
    "get_auth_token_repository",
    "get_dashboard_repository",
    # Services
    "get_account_service",
    "get_jwt_service",
    # Account
    "get_create_account_handler",
    "get_update_account_handler",
    "get_delete_account_handler",
    "get_state_account_handler",
    "get_user_accounts_handler",
    "get_account_by_id_handler",
    "get_activity_account_handler",
    # Transaction
    "get_transactions_handler",
    "get_transaction_by_uuid_handler",
    "get_create_transaction_handler",
    "get_update_transaction_handler",
    "get_delete_transaction_handler",
    # Subscription
    "get_create_subscription_handler",
    "get_update_subscription_handler",
    "get_state_subscription_handler",
    "get_subscriptions_handler",
    "get_subscription_by_id_handler",
    "get_subscription_charges_handler",
    "get_delete_subscription_handler",
    "get_last_transactions_handler",
    # Category
    "get_categories_handler",
    # Dashboard
    "get_dashboard_summary_handler",
    # Auth handlers
    "get_login_handler",
    "get_register_handler",
    "get_refresh_token_handler",
    "get_logout_handler",
    # Auth validation
    "get_current_user",
    "get_current_active_user",
    "validate_token",
    # Bank
    "get_banks_handler",
    # AI
    "get_analyze_image_handler",
    "get_expense_advisor_handler",
]
