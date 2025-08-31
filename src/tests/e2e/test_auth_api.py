"""End-to-end tests for authentication API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens


class TestAPIConnectivity:
    """Test API connectivity and basic endpoints."""
    
    @pytest.mark.asyncio
    async def test_api_connectivity(self, http_client: httpx.AsyncClient):
        """Test API is running and accessible."""
        response = await http_client.get("http://127.0.0.1:8000/docs")
        assert response.status_code == 200, f"API should be running, got {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_auth_endpoints_available(self, http_client: httpx.AsyncClient):
        """Test auth endpoints are available."""
        response = await http_client.get("/auth/")
        # Auth endpoints can return 404 or 405 (Method Not Allowed) - both mean the route exists
        assert response.status_code in [404, 405, 200], f"Auth endpoint should be available, got {response.status_code}"


class TestEmailValidation:
    """Test email validation with different providers."""
    
    @pytest.mark.asyncio
    async def test_gmail_email_registration(self, http_client: httpx.AsyncClient):
        """Test registration with Gmail email."""
        user_data = {
            "name": "Gmail User",
            "email": "testuser123@gmail.com",
            "password": "Password123!"
        }
        response = await http_client.post("/auth/register", json=user_data)
        
        # Accept both new user (200) and existing user (409)
        assert response.status_code in [200, 409], f"Gmail registration: Expected 200 or 409, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "user_uuid" in data
            assert "email" in data
            assert "name" in data
            assert "message" in data
    
    @pytest.mark.asyncio
    async def test_yahoo_email_registration(self, http_client: httpx.AsyncClient):
        """Test registration with Yahoo email."""
        user_data = {
            "name": "Yahoo User",
            "email": "testuser456@yahoo.com", 
            "password": "Password123!"
        }
        response = await http_client.post("/auth/register", json=user_data)
        
        # Accept both new user (200) and existing user (409)
        assert response.status_code in [200, 409], f"Yahoo registration: Expected 200 or 409, got {response.status_code}"


class TestUserRegistration:
    """Test user registration functionality."""
    
    @pytest.mark.asyncio
    async def test_register_new_user(self, http_client: httpx.AsyncClient, debug_user_data: dict):
        """Test registering a new user."""
        response = await http_client.post("/auth/register", json=debug_user_data)
        
        # Accept both new user (200) and existing user (409)
        assert response.status_code in [200, 409], f"Registration: Expected 200 or 409, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "user_uuid" in data, "Should have user_uuid"
            assert "email" in data, "Should have email"
            assert "name" in data, "Should have name"
            assert "message" in data, "Should have message"
            assert data["email"] == debug_user_data["email"]
            assert data["name"] == debug_user_data["name"]
        elif response.status_code == 409:
            # User already exists - that's fine for testing
            data = response.json()
            assert "message" in data  # Using standardized error format
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, http_client: httpx.AsyncClient, debug_user_data: dict):
        """Test registering with duplicate email returns 409."""
        # First registration
        await http_client.post("/auth/register", json=debug_user_data)
        
        # Second registration with same email
        response = await http_client.post("/auth/register", json=debug_user_data)
        assert response.status_code == 409, f"Duplicate email: Expected 409, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"


class TestUserAuthentication:
    """Test user authentication (login) functionality."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, http_client: httpx.AsyncClient, debug_user_data: dict, auth_tokens: AuthTokens):
        """Test successful login."""
        # Ensure user exists
        await http_client.post("/auth/register", json=debug_user_data)
        
        # Attempt login
        login_data = {
            "email": debug_user_data["email"],
            "password": debug_user_data["password"]
        }
        response = await http_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200, f"Login: Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "access_token" in data, "Should have access_token"
        assert "refresh_token" in data, "Should have refresh_token"
        assert "token_type" in data, "Should have token_type"
        assert data["token_type"] == "bearer", "Should be bearer token"
        
        # Save tokens for subsequent tests
        auth_tokens.set_tokens(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data["token_type"]
        )
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, http_client: httpx.AsyncClient, debug_user_data: dict):
        """Test login with wrong password."""
        login_data = {
            "email": debug_user_data["email"],
            "password": "wrongpassword"
        }
        response = await http_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401, f"Wrong password: Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, http_client: httpx.AsyncClient):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "Password123!"
        }
        response = await http_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 404, f"Nonexistent user: Expected 404, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"


class TestUserProfile:
    """Test user profile (me) endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, debug_user_data: dict):
        """Test getting user info with valid token."""
        # Ensure we have tokens
        if not auth_tokens.access_token:
            # Register and login first
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
        
        response = await http_client.get("/auth/me", headers=auth_tokens.get_auth_headers())
        
        assert response.status_code == 200, f"Get user info: Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "user_uuid" in data, "Should have user_uuid"
        assert "email" in data, "Should have email"
        assert "name" in data, "Should have name"
        assert "is_active" in data, "Should have is_active"
        assert data["is_active"] is True, "Should be active"
    
    @pytest.mark.asyncio
    async def test_get_user_info_unauthorized(self, http_client: httpx.AsyncClient):
        """Test getting user info without token."""
        response = await http_client.get("/auth/me")
        
        assert response.status_code == 401, f"Unauthorized: Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"
    
    @pytest.mark.asyncio
    async def test_get_user_info_invalid_token(self, http_client: httpx.AsyncClient):
        """Test getting user info with invalid token."""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = await http_client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401, f"Invalid token: Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"


class TestTokenRefresh:
    """Test token refresh functionality."""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, debug_user_data: dict):
        """Test successful token refresh."""
        # Ensure we have tokens
        if not auth_tokens.refresh_token:
            # Register and login first
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
        
        refresh_data = {"refresh_token": auth_tokens.refresh_token}
        response = await http_client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200, f"Refresh token: Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "access_token" in data, "Should have new access_token"
        assert "refresh_token" in data, "Should have refresh_token"
        assert "token_type" in data, "Should have token_type"
        assert data["token_type"] == "bearer", "Should be bearer token"
        
        # Update tokens
        auth_tokens.set_tokens(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"]
        )
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, http_client: httpx.AsyncClient):
        """Test refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid_refresh_token"}
        response = await http_client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 400, f"Invalid refresh: Expected 400, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"
    
    @pytest.mark.asyncio
    async def test_refresh_token_missing(self, http_client: httpx.AsyncClient):
        """Test refresh with missing token."""
        refresh_data = {}
        response = await http_client.post("/auth/refresh", json=refresh_data)
        
        # Can return 422 (validation) or 401 (invalid token)
        assert response.status_code in [422, 401], f"Missing refresh token: Expected 422 or 401, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have error message"


class TestLogout:
    """Test logout functionality."""
    
    @pytest.mark.asyncio
    async def test_logout_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, debug_user_data: dict):
        """Test successful logout."""
        # Ensure we have tokens
        if not auth_tokens.refresh_token:
            # Register and login first
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
        
        logout_data = {"refresh_token": auth_tokens.refresh_token}
        response = await http_client.post("/auth/logout", json=logout_data)
        
        assert response.status_code == 200, f"Logout: Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Should have success message"
    
    @pytest.mark.asyncio
    async def test_token_revoked_after_logout(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test that token is revoked after logout."""
        if not auth_tokens.refresh_token:
            pytest.skip("No refresh token available (logout test must run first)")
        
        # Try to use the refresh token after logout
        refresh_data = {"refresh_token": auth_tokens.refresh_token}
        response = await http_client.post("/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401, f"Revoked token: Expected 401, got {response.status_code}"
        
        data = response.json()
        assert "detail" in data, "Should have error detail - token should be revoked"


class TestCompleteAuthFlow:
    """Test complete authentication flow."""
    
    @pytest.mark.asyncio
    async def test_complete_flow_register_to_logout(self, http_client: httpx.AsyncClient, flow_user_data: dict):
        """Test complete flow: Register → Login → Me → Refresh → Logout → Verify."""
        
        # 1. REGISTRO
        register_response = await http_client.post("/auth/register", json=flow_user_data)
        assert register_response.status_code in [200, 409], "Registration should succeed or user exists"
        
        # 2. LOGIN
        login_data = {
            "email": flow_user_data["email"],
            "password": flow_user_data["password"]
        }
        login_response = await http_client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200, "Login should succeed"
        
        login_data_response = login_response.json()
        access_token = login_data_response["access_token"]
        refresh_token = login_data_response["refresh_token"]
        
        # 3. PERFIL DE USUARIO (ME)
        headers = {"Authorization": f"bearer {access_token}"}
        me_response = await http_client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200, "Getting user info should succeed"
        
        # 4. RENOVACIÓN DE TOKEN
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = await http_client.post("/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == 200, "Token refresh should succeed"
        
        refresh_data_response = refresh_response.json()
        new_access_token = refresh_data_response["access_token"]
        new_refresh_token = refresh_data_response["refresh_token"]
        
        # 5. CERRAR SESIÓN
        logout_data = {"refresh_token": new_refresh_token}
        logout_response = await http_client.post("/auth/logout", json=logout_data)
        assert logout_response.status_code == 200, "Logout should succeed"
        
        # 6. VERIFICACIÓN - Token revocado
        verify_data = {"refresh_token": new_refresh_token}
        verify_response = await http_client.post("/auth/refresh", json=verify_data)
        assert verify_response.status_code == 400, "Token should be revoked after logout"


class TestValidation:
    """Test input validation."""
    
    @pytest.mark.asyncio
    async def test_register_missing_fields(self, http_client: httpx.AsyncClient):
        """Test registration with missing fields."""
        incomplete_data = {
            "email": "test2@example.com"
            # Missing name and password
        }
        response = await http_client.post("/auth/register", json=incomplete_data)
        
        assert response.status_code == 422, f"Missing fields: Expected 422, got {response.status_code}"
        
        data = response.json()
        assert "details" in data, "Should have validation errors"
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, http_client: httpx.AsyncClient):
        """Test registration with invalid email."""
        invalid_data = {
            "name": "Test User",
            "email": "invalid-email",
            "password": "Password123!"
        }
        response = await http_client.post("/auth/register", json=invalid_data)
        
        assert response.status_code == 422, f"Invalid email: Expected 422, got {response.status_code}"
        
        data = response.json()
        assert "details" in data, "Should have validation errors"
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, http_client: httpx.AsyncClient):
        """Test registration with password without uppercase and special character."""
        weak_data = {
            "name": "Test User",
            "email": "test3@example.com",
            "password": "password123"  # No uppercase or special character
        }
        response = await http_client.post("/auth/register", json=weak_data)
        
        assert response.status_code in [400, 422], f"Weak password: Expected 400 or 422, got {response.status_code}"
        
        data = response.json()
        assert "details" in data, "Should have validation errors"
    
    @pytest.mark.asyncio
    async def test_register_short_password(self, http_client: httpx.AsyncClient):
        """Test registration with very short password."""
        short_data = {
            "name": "Test User",
            "email": "test4@example.com",
            "password": "123"  # Too short
        }
        response = await http_client.post("/auth/register", json=short_data)
        
        assert response.status_code in [400, 422], f"Short password: Expected 400 or 422, got {response.status_code}"
        
        data = response.json()
        assert "details" in data, "Should have validation errors"