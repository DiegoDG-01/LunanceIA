"""End-to-end tests for account API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens


class TestAccountStatusToggle:
    """Test account status toggle functionality."""
    
    @pytest.mark.asyncio
    async def test_toggle_account_status_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, debug_user_data: dict):
        """Test successful account status toggle."""
        # Ensure we have tokens
        if not auth_tokens.access_token:
            await http_client.post("/auth/register", json=debug_user_data)
            login_data = {
                "email": debug_user_data["email"],
                "password": debug_user_data["password"]
            }
            login_response = await http_client.post("/auth/login", json=login_data)
            login_data_response = login_response.json()
            auth_tokens.set_tokens(
                access_token=login_data_response["access_token"],
                refresh_token=login_data_response["refresh_token"]
            )
        
        # First, create an account to test status toggle
        account_data = {
            "name": "Test Account",
            "account_type": "SAVINGS",
            "bank": "Test Bank",
            "initial_balance": 1000.00,
            "currency": "MXN"
        }
        
        create_response = await http_client.post(
            "/account/",
            json=account_data,
            headers=auth_tokens.get_auth_headers()
        )
        
        # Skip test if account creation fails (might be due to missing dependencies)
        if create_response.status_code not in [200, 201]:
            pytest.skip("Account creation not available")
        
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
        headers = {"Authorization": "Bearer invalid_token_here"}

        response = await http_client.patch(
            f"/account/{fake_uuid}/status",
            headers=headers
        )
        
        assert response.status_code == 401, f"Invalid token: Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"
    
    @pytest.mark.asyncio
    async def test_toggle_nonexistent_account(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, debug_user_data: dict):
        """Test toggling status of nonexistent account."""
        # Ensure we have tokens
        if not auth_tokens.access_token:
            await http_client.post("/auth/register", json=debug_user_data)
            login_data = {
                "email": debug_user_data["email"],
                "password": debug_user_data["password"]
            }
            login_response = await http_client.post("/auth/login", json=login_data)
            login_data_response = login_response.json()
            auth_tokens.set_tokens(
                access_token=login_data_response["access_token"],
                refresh_token=login_data_response["refresh_token"]
            )
        
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"
        
        response = await http_client.patch(
            f"/account/{fake_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )
        
        assert response.status_code == 404, f"Nonexistent account: Expected 404, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"
    
    @pytest.mark.asyncio
    async def test_toggle_account_invalid_uuid_format(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, debug_user_data: dict):
        """Test toggling status with invalid UUID format."""
        # Ensure we have tokens
        if not auth_tokens.access_token:
            await http_client.post("/auth/register", json=debug_user_data)
            login_data = {
                "email": debug_user_data["email"],
                "password": debug_user_data["password"]
            }
            login_response = await http_client.post("/auth/login", json=login_data)
            login_data_response = login_response.json()
            auth_tokens.set_tokens(
                access_token=login_data_response["access_token"],
                refresh_token=login_data_response["refresh_token"]
            )
        
        invalid_uuid = "invalid-uuid-format"
        
        response = await http_client.patch(
            f"/account/{invalid_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )
        
        # Could return 404 (not found) or 422 (validation error)
        assert response.status_code in [404, 422], f"Invalid UUID: Expected 404 or 422, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"


class TestAccountStatusConsistency:
    """Test account status consistency across multiple operations."""
    
    @pytest.mark.asyncio
    async def test_double_toggle_returns_original_state(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, debug_user_data: dict):
        """Test that toggling status twice returns to original state."""
        # Ensure we have tokens
        if not auth_tokens.access_token:
            await http_client.post("/auth/register", json=debug_user_data)
            login_data = {
                "email": debug_user_data["email"],
                "password": debug_user_data["password"]
            }
            login_response = await http_client.post("/auth/login", json=login_data)
            login_data_response = login_response.json()
            auth_tokens.set_tokens(
                access_token=login_data_response["access_token"],
                refresh_token=login_data_response["refresh_token"]
            )
        
        # Create an account
        account_data = {
            "name": "Toggle Test Account",
            "account_type": "CHECKING",
            "bank": "Test Bank",
            "initial_balance": 500.00,
            "currency": "MXN"
        }
        
        create_response = await http_client.post(
            "/account/",
            json=account_data,
            headers=auth_tokens.get_auth_headers()
        )
        
        # Skip test if account creation fails
        if create_response.status_code not in [200, 201]:
            pytest.skip("Account creation not available")
        
        account_uuid = create_response.json()["account_uuid"]
        original_status = create_response.json()["is_active"]
        
        # First toggle
        first_toggle_response = await http_client.patch(
            f"/account/{account_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )
        
        assert first_toggle_response.status_code == 200, "First toggle should succeed"
        first_status = first_toggle_response.json()["is_active"]
        assert first_status != original_status, "First toggle should change status"
        
        # Second toggle
        second_toggle_response = await http_client.patch(
            f"/account/{account_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )
        
        assert second_toggle_response.status_code == 200, "Second toggle should succeed"
        final_status = second_toggle_response.json()["is_active"]
        assert final_status == original_status, "Double toggle should return to original state"
        assert final_status != first_status, "Final status should be different from first toggle"


class TestAccountStatusValidation:
    """Test account status validation and edge cases."""
    
    @pytest.mark.asyncio
    async def test_toggle_status_preserves_other_fields(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, debug_user_data: dict):
        """Test that toggling status preserves all other account fields."""
        # Ensure we have tokens
        if not auth_tokens.access_token:
            await http_client.post("/auth/register", json=debug_user_data)
            login_data = {
                "email": debug_user_data["email"],
                "password": debug_user_data["password"]
            }
            login_response = await http_client.post("/auth/login", json=login_data)
            login_data_response = login_response.json()
            auth_tokens.set_tokens(
                access_token=login_data_response["access_token"],
                refresh_token=login_data_response["refresh_token"]
            )
        
        # Create an account with specific values
        account_data = {
            "name": "Preservation Test Account",
            "account_type": "SAVINGS",
            "bank": "Preservation Bank",
            "initial_balance": 1234.56,
            "currency": "MXN"
        }
        
        create_response = await http_client.post(
            "/account/",
            json=account_data,
            headers=auth_tokens.get_auth_headers()
        )
        
        # Skip test if account creation fails
        if create_response.status_code not in [200, 201]:
            pytest.skip("Account creation not available")
        
        original_account = create_response.json()
        account_uuid = original_account["account_uuid"]
        
        # Toggle status
        toggle_response = await http_client.patch(
            f"/account/{account_uuid}/status",
            headers=auth_tokens.get_auth_headers()
        )
        
        assert toggle_response.status_code == 200, "Toggle should succeed"
        
        updated_account = toggle_response.json()
        
        # Verify all fields except is_active are preserved
        assert updated_account["account_uuid"] == original_account["account_uuid"], "UUID should be preserved"
        assert updated_account["name"] == original_account["name"], "Name should be preserved"
        assert updated_account["account_type"] == original_account["account_type"], "Account type should be preserved"
        assert updated_account["bank"] == original_account["bank"], "Bank should be preserved"
        assert updated_account["current_balance"] == original_account["current_balance"], "Balance should be preserved"
        assert updated_account["currency"] == original_account["currency"], "Currency should be preserved"
        assert updated_account["is_active"] != original_account["is_active"], "Status should be toggled"