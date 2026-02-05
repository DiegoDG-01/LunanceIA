"""End-to-end tests for account API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens


class TestAccountStatusToggle:
    """Test account status toggle functionality."""

    @pytest.mark.asyncio
    async def test_toggle_account_status_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test successful account status toggle."""
        # First, create an account to test status toggle
        account_data = {
            "name": "Test Account",
            "account_type": "SAVINGS",
            "bank_id": None,
            "initial_balance": 1000.00,
            "currency": "MXN"
        }

        create_response = await http_client.post(
            "/account",
            json=account_data,
            headers=auth_tokens.get_auth_headers()
        )

        assert create_response.status_code in [200, 201], f"Account creation failed: {create_response.text}"

        account_uuid = create_response.json()["account_uuid"]
        original_status = create_response.json()["is_active"]

        # Toggle account status
        response = await http_client.patch(
            f"/account/{account_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200, f"Status toggle: Expected 200, got {response.status_code}"

        data = response.json()
        assert "account_uuid" in data, "Should have account_uuid"
        assert "is_active" in data, "Should have is_active"
        assert data["account_uuid"] == account_uuid, "Should return correct account"
        assert data["is_active"] != original_status, "Status should be toggled"

    @pytest.mark.asyncio
    async def test_toggle_account_status_unauthorized(self, http_client: httpx.AsyncClient):
        """Test account status toggle without authentication."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"

        response = await http_client.patch(f"/account/{fake_uuid}/status")

        assert response.status_code == 401, f"Unauthorized: Expected 401, got {response.status_code}"

        data = response.json()
        assert "message" in data, "Should have error message"

    @pytest.mark.asyncio
    async def test_toggle_account_status_invalid_token(self, http_client: httpx.AsyncClient):
        """Test account status toggle with invalid token."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer invalid-token"}

        response = await http_client.patch(
            f"/account/{fake_uuid}/status",
            headers=headers
        )

        assert response.status_code == 401, f"Invalid token: Expected 401, got {response.status_code}"

        data = response.json()
        assert "message" in data, "Should have error message"

    @pytest.mark.asyncio
    async def test_toggle_nonexistent_account(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test toggling status of nonexistent account."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"

        response = await http_client.patch(
            f"/account/{fake_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 404, f"Nonexistent account: Expected 404, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_toggle_account_invalid_uuid_format(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test toggling status with invalid UUID format."""
        invalid_uuid = "invalid-uuid-format"

        response = await http_client.patch(
            f"/account/{invalid_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )

        # FastAPI might return 404 or 422 for path param validation
        assert response.status_code in [404, 422], f"Invalid UUID: Expected 404 or 422, got {response.status_code}"


class TestAccountStatusConsistency:
    """Test account status consistency across multiple operations."""

    @pytest.mark.asyncio
    async def test_double_toggle_returns_original_state(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test that toggling status twice returns to original state."""
        # Create an account
        account_data = {
            "name": "Toggle Test Account",
            "account_type": "CHECKING",
            "bank_id": None,
            "initial_balance": 500.00,
            "currency": "MXN"
        }

        create_response = await http_client.post(
            "/account",
            json=account_data,
            headers=auth_tokens.get_auth_headers()
        )

        assert create_response.status_code in [200, 201]

        account_uuid = create_response.json()["account_uuid"]
        original_status = create_response.json()["is_active"]

        # First toggle
        first_toggle_response = await http_client.patch(
            f"/account/{account_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )

        assert first_toggle_response.status_code == 200
        first_status = first_toggle_response.json()["is_active"]
        assert first_status != original_status

        # Second toggle
        second_toggle_response = await http_client.patch(
            f"/account/{account_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )

        assert second_toggle_response.status_code == 200
        final_status = second_toggle_response.json()["is_active"]
        assert final_status == original_status


class TestAccountStatusValidation:
    """Test account status validation and edge cases."""

    @pytest.mark.asyncio
    async def test_toggle_status_preserves_other_fields(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test that toggling status preserves all other account fields."""
        # Create an account with specific values
        account_data = {
            "name": "Preservation Test Account",
            "account_type": "SAVINGS",
            "bank_id": None,
            "initial_balance": 1234.56,
            "currency": "MXN"
        }

        create_response = await http_client.post(
            "/account",
            json=account_data,
            headers=auth_tokens.get_auth_headers()
        )

        assert create_response.status_code in [200, 201]

        original_account = create_response.json()
        account_uuid = original_account["account_uuid"]

        # Toggle status
        toggle_response = await http_client.patch(
            f"/account/{account_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )

        assert toggle_response.status_code == 200

        updated_account = toggle_response.json()

        # Verify all fields except is_active are preserved
        assert updated_account["account_uuid"] == original_account["account_uuid"]
        assert updated_account["name"] == original_account["name"]
        assert updated_account["account_type"] == original_account["account_type"]
        assert updated_account["bank_id"] == original_account["bank_id"]
        assert updated_account["current_balance"] == original_account["current_balance"]
        assert updated_account["currency"] == original_account["currency"]
        assert updated_account["is_active"] != original_account["is_active"]
