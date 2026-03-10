"""End-to-end tests for edge cases and security boundaries."""

import pytest
import httpx
from ..conftest import AuthTokens, MOCK_USER_ID
from infrastructure.database.models.account import AccountModel
from infrastructure.database.models.user import UserModel
from domain.objects.enums import AccountType

@pytest.mark.e2e
class TestSecurityBoundaries:
    """Test that users cannot access resources belonging to other users."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_user_account(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, db_session):
        """Test that a user receives 404 when trying to access an account owned by someone else."""

        # 1. Create another user and their account directly in the DB
        other_user = UserModel(
            id=999,
            uuid="other-user-uuid",
            auth0_id="auth0|other",
            name="Other User",
            email="other@test.com"
        )
        db_session.add(other_user)
        await db_session.commit()

        other_account = AccountModel(
            uuid="stolen-account-uuid",
            user_id=other_user.id,
            bank_id=1,
            name="Private Account",
            type=AccountType.CHECKING,
            current_balance=5000.0,
            currency="MXN"
        )
        db_session.add(other_account)
        await db_session.commit()

        # 2. Try to access it with our standard mock user (ID=1)
        response = await http_client.get(
            f"/account/{other_account.uuid}",
            headers=auth_tokens.get_auth_headers()
        )

        # Clean Architecture standard: Return 404 to not leak existence of records
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_delete_other_user_transaction(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, db_session):
        """Test that a user cannot delete a transaction they don't own."""
        from infrastructure.database.models.transaction import TransactionModel
        from datetime import date

        # 1. Create a transaction for user 999
        other_tx = TransactionModel(
            uuid="other-tx-uuid",
            user_id=999, # Other user created in previous test or setup
            account_id=1, # Doesn't matter for this logic check
            category_id=1,
            type="EXPENSE",
            amount=100.0,
            transaction_date=date.today(),
            description="Other's tx"
        )
        db_session.add(other_tx)
        await db_session.commit()

        # 2. Try to delete it
        response = await http_client.delete(
            f"/transaction/{other_tx.uuid}",
            headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 404

@pytest.mark.e2e
class TestBusinessLogicEdges:
    """Test boundary conditions in financial logic."""

    @pytest.mark.asyncio
    async def test_insufficient_funds_error(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test that creating an expense larger than balance returns a business error."""

        # 1. Create account with small balance
        acc_res = await http_client.post("/account", json={
            "name": "Small Account",
            "account_type": "CASH",
            "bank_id": 1,
            "initial_balance": 10.00,
            "currency": "MXN"
        }, headers=auth_tokens.get_auth_headers())
        account_uuid = acc_res.json()["account_uuid"]

        # 2. Try to spend more than 10.00
        response = await http_client.post("/transaction", json={
            "account_uuid": account_uuid,
            "category_id": 1,
            "transaction_type": "EXPENSE",
            "amount": 100.00,
            "description": "Too expensive"
        }, headers=auth_tokens.get_auth_headers())

        # Should return 400 (Bad Request) or 422 (Unprocessable) with business error
        assert response.status_code in [400, 409, 422]
        data = response.json()
        assert data["error"] is True
        # Verify it uses our domain exception code
        assert "BUSINESS" in data["error_code"] or "FUNDS" in data["error_code"]
