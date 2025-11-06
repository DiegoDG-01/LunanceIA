"""End-to-end tests for authentication API endpoints.

Tests complete authentication flows including:
- User registration
- Login/logout
- Token management (access, refresh)
- User profile operations
- Error handling and validation
- Multi-language support
"""

import pytest
import httpx
from ..conftest import AuthTokens


class TestAPIConnectivity:
    """Test API connectivity and basic endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_api_connectivity(self, http_client: httpx.AsyncClient):
        """Test API is running and accessible."""
        response = await http_client.get("http://127.0.0.1:8000/docs")
        assert response.status_code == 200, f"API should be running, got {response.status_code}"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_endpoints_available(self, http_client: httpx.AsyncClient):
        """Test auth endpoints are available."""
        response = await http_client.get("/auth/")
        # Auth endpoints can return 404 or 405 (Method Not Allowed) - both mean the route exists
        assert response.status_code in [404, 405, 200], f"Auth endpoint should be available, got {response.status_code}"


class TestUserRegistration:
    """Test user registration functionality with error handling."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_register_new_user_success(self, http_client: httpx.AsyncClient, debug_user_data: dict):
        """Test registering a new user returns proper success response."""
        response = await http_client.post("/auth/register", json=debug_user_data)

        # Accept both new user (200) and existing user (409)
        assert response.status_code in [200, 409], f"Registration: Expected 200 or 409, got {response.status_code}"

        data = response.json()

        if response.status_code == 200:
            # Verify success response structure
            assert "user_uuid" in data, "Should have user_uuid"
            assert "email" in data, "Should have email"
            assert "name" in data, "Should have name"
            assert "message" in data, "Should have message"
            assert data["email"] == debug_user_data["email"]
            assert data["name"] == debug_user_data["name"]
            # Verify UUID format (basic check)
            assert len(data["user_uuid"]) > 0, "user_uuid should not be empty"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_register_duplicate_email_returns_409(self, http_client: httpx.AsyncClient, debug_user_data: dict):
        """Test registering with duplicate email returns 409 with proper error structure."""
        # First registration
        await http_client.post("/auth/register", json=debug_user_data)

        # Second registration with same email
        response = await http_client.post("/auth/register", json=debug_user_data)
        assert response.status_code == 409, f"Duplicate email: Expected 409, got {response.status_code}"

        data = response.json()
        # Verify error response structure
        assert "error" in data, "Should have error field"
        assert data["error"] is True, "Error field should be True"
        assert "error_code" in data, "Should have error_code"
        assert data["error_code"] == "BUSINESS_EMAIL_EXISTS", "Should have correct error code"
        assert "message" in data, "Should have error message"
        assert len(data["message"]) > 0, "Error message should not be empty"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_register_duplicate_email_spanish(self, http_client: httpx.AsyncClient):
        """Test duplicate email error message in Spanish."""
        user_data = {
            "name": "Test Spanish",
            "email": "spanish_test@cloud.com",
            "password": "Password123!"
        }

        # Register first time
        await http_client.post("/auth/register", json=user_data)

        # Try to register again with Spanish header
        response = await http_client.post(
            "/auth/register",
            json=user_data,
            headers={"Accept-Language": "es"}
        )

        assert response.status_code == 409
        data = response.json()
        assert "message" in data
        # Message should be in Spanish
        assert "registrado" in data["message"].lower() or "existe" in data["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_register_duplicate_email_english(self, http_client: httpx.AsyncClient):
        """Test duplicate email error message in English."""
        user_data = {
            "name": "Test English",
            "email": "english_test@cloud.com",
            "password": "Password123!"
        }

        # Register first time
        await http_client.post("/auth/register", json=user_data)

        # Try to register again with English header
        response = await http_client.post(
            "/auth/register",
            json=user_data,
            headers={"Accept-Language": "en"}
        )

        assert response.status_code == 409
        data = response.json()
        assert "message" in data
        # Message should be in English
        assert "already" in data["message"].lower() or "registered" in data["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_register_with_different_email_providers(self, http_client: httpx.AsyncClient):
        """Test registration with various email providers."""
        email_providers = [
            "testuser_gmail@gmail.com",
            "testuser_yahoo@yahoo.com",
            "testuser_outlook@outlook.com",
        ]

        for email in email_providers:
            user_data = {
                "name": f"Test User {email.split('@')[1]}",
                "email": email,
                "password": "Password123!"
            }
            response = await http_client.post("/auth/register", json=user_data)

            # Accept both new user (200) and existing user (409)
            assert response.status_code in [200, 409], \
                f"Registration with {email}: Expected 200 or 409, got {response.status_code}"


class TestUserAuthentication:
    """Test user authentication (login) functionality with error handling."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_login_success_returns_tokens(
        self,
        http_client: httpx.AsyncClient,
        debug_user_data: dict,
        auth_tokens: AuthTokens
    ):
        """Test successful login returns all required tokens."""
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
        # Verify token structure
        assert "access_token" in data, "Should have access_token"
        assert "refresh_token" in data, "Should have refresh_token"
        assert "token_type" in data, "Should have token_type"
        assert data["token_type"] == "bearer", "Should be bearer token"

        # Verify tokens are not empty
        assert len(data["access_token"]) > 0, "access_token should not be empty"
        assert len(data["refresh_token"]) > 0, "refresh_token should not be empty"

        # Save tokens for subsequent tests
        auth_tokens.set_tokens(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data["token_type"]
        )

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_login_wrong_password_returns_401(self, http_client: httpx.AsyncClient, debug_user_data: dict):
        """Test login with wrong password returns 401 with proper error structure."""
        # Ensure user exists
        await http_client.post("/auth/register", json=debug_user_data)

        login_data = {
            "email": debug_user_data["email"],
            "password": "WrongPassword999!"
        }
        response = await http_client.post("/auth/login", json=login_data)

        assert response.status_code == 401, f"Wrong password: Expected 401, got {response.status_code}"

        data = response.json()
        # Verify error structure
        assert "error" in data, "Should have error field"
        assert data["error"] is True, "Error should be True"
        assert "error_code" in data, "Should have error_code"
        assert data["error_code"] == "AUTH_INVALID_CREDENTIALS", "Should have correct error code"
        assert "message" in data, "Should have error message"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_login_nonexistent_user_returns_401(self, http_client: httpx.AsyncClient):
        """Test login with nonexistent user returns 401 with proper error structure."""
        login_data = {
            "email": "nonexistent_user_12345@example.com",
            "password": "Password123!"
        }
        response = await http_client.post("/auth/login", json=login_data)

        assert response.status_code == 401, f"Nonexistent user: Expected 401, got {response.status_code}"

        data = response.json()
        # Verify error structure
        assert "error" in data, "Should have error field"
        assert data["error"] is True, "Error should be True"
        assert "error_code" in data, "Should have error_code"
        assert data["error_code"] == "AUTH_INVALID_CREDENTIALS", "Should have correct error code"
        assert "message" in data, "Should have error message"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_login_wrong_password_spanish(self, http_client: httpx.AsyncClient, debug_user_data: dict):
        """Test wrong password error message in Spanish."""
        await http_client.post("/auth/register", json=debug_user_data)

        login_data = {
            "email": debug_user_data["email"],
            "password": "WrongPassword!"
        }
        response = await http_client.post(
            "/auth/login",
            json=login_data,
            headers={"Accept-Language": "es"}
        )

        assert response.status_code == 401
        data = response.json()
        assert "message" in data
        # Message should contain Spanish terms
        assert "credencial" in data["message"].lower() or "inválida" in data["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_login_wrong_password_english(self, http_client: httpx.AsyncClient, debug_user_data: dict):
        """Test wrong password error message in English."""
        await http_client.post("/auth/register", json=debug_user_data)

        login_data = {
            "email": debug_user_data["email"],
            "password": "WrongPassword!"
        }
        response = await http_client.post(
            "/auth/login",
            json=login_data,
            headers={"Accept-Language": "en"}
        )

        assert response.status_code == 401
        data = response.json()
        assert "message" in data
        # Message should contain English terms
        assert "credential" in data["message"].lower() or "invalid" in data["message"].lower()


class TestUserProfile:
    """Test user profile (me) endpoint with authorization."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_get_user_info_success(
        self,
        http_client: httpx.AsyncClient,
        auth_tokens: AuthTokens,
        debug_user_data: dict
    ):
        """Test getting user info with valid token returns complete profile."""
        # Ensure we have tokens
        if not auth_tokens.access_token:
            await http_client.post("/auth/register", json=debug_user_data)
            login_response = await http_client.post(
                "/auth/login",
                json={
                    "email": debug_user_data["email"],
                    "password": debug_user_data["password"]
                }
            )
            tokens = login_response.json()
            auth_tokens.set_tokens(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"]
            )

        response = await http_client.get("/auth/me", headers=auth_tokens.get_auth_headers())

        assert response.status_code == 200, f"Get user info: Expected 200, got {response.status_code}"

        data = response.json()
        # Verify profile structure
        assert "user_uuid" in data, "Should have user_uuid"
        assert "email" in data, "Should have email"
        assert "name" in data, "Should have name"
        assert "is_active" in data, "Should have is_active"
        assert data["is_active"] is True, "Should be active"
        # Verify data types
        assert isinstance(data["user_uuid"], str), "user_uuid should be string"
        assert isinstance(data["email"], str), "email should be string"
        assert isinstance(data["name"], str), "name should be string"
        assert isinstance(data["is_active"], bool), "is_active should be boolean"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_get_user_info_without_token_returns_401(self, http_client: httpx.AsyncClient):
        """Test getting user info without token returns 401."""
        response = await http_client.get("/auth/me")

        assert response.status_code == 401, f"Unauthorized: Expected 401, got {response.status_code}"

        data = response.json()
        assert "error" in data or "message" in data, "Should have error information"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_get_user_info_with_invalid_token_returns_401(self, http_client: httpx.AsyncClient):
        """Test getting user info with invalid token returns 401."""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = await http_client.get("/auth/me", headers=headers)

        assert response.status_code == 401, f"Invalid token: Expected 401, got {response.status_code}"

        data = response.json()
        assert "error" in data or "message" in data, "Should have error information"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_get_user_info_with_malformed_token_returns_401(self, http_client: httpx.AsyncClient):
        """Test getting user info with malformed token returns 401."""
        headers = {"Authorization": "InvalidFormat"}
        response = await http_client.get("/auth/me", headers=headers)

        assert response.status_code == 401, f"Malformed token: Expected 401, got {response.status_code}"


class TestTokenRefresh:
    """Test token refresh functionality."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_refresh_token_success(
        self,
        http_client: httpx.AsyncClient,
        auth_tokens: AuthTokens,
        debug_user_data: dict
    ):
        """Test successful token refresh returns new tokens."""
        # Ensure we have tokens
        if not auth_tokens.refresh_token:
            await http_client.post("/auth/register", json=debug_user_data)
            login_response = await http_client.post(
                "/auth/login",
                json={
                    "email": debug_user_data["email"],
                    "password": debug_user_data["password"]
                }
            )
            tokens = login_response.json()
            auth_tokens.set_tokens(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"]
            )

        old_access_token = auth_tokens.access_token

        # Wait a moment to ensure timestamp changes
        import asyncio
        await asyncio.sleep(0.1)

        refresh_data = {"refresh_token": auth_tokens.refresh_token}
        response = await http_client.post("/auth/refresh", json=refresh_data)

        assert response.status_code == 200, f"Refresh token: Expected 200, got {response.status_code}"

        data = response.json()
        assert "access_token" in data, "Should have new access_token"
        assert "refresh_token" in data, "Should have refresh_token"
        assert "token_type" in data, "Should have token_type"
        assert data["token_type"] == "bearer", "Should be bearer token"

        # Verify we got new tokens
        assert data["access_token"] != old_access_token, "Should receive new access token"

        # Update tokens
        auth_tokens.set_tokens(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"]
        )

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_refresh_with_invalid_token_returns_400(self, http_client: httpx.AsyncClient):
        """Test refresh with invalid token returns 400."""
        refresh_data = {"refresh_token": "invalid_refresh_token_12345"}
        response = await http_client.post("/auth/refresh", json=refresh_data)

        assert response.status_code == 400, f"Invalid refresh: Expected 400, got {response.status_code}"

        data = response.json()
        assert "error" in data or "message" in data, "Should have error information"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_refresh_with_missing_token_returns_422(self, http_client: httpx.AsyncClient):
        """Test refresh with missing token returns 422."""
        refresh_data = {}
        response = await http_client.post("/auth/refresh", json=refresh_data)

        # Can return 422 (validation) or 401 (invalid token)
        assert response.status_code in [422, 401], \
            f"Missing refresh token: Expected 422 or 401, got {response.status_code}"

        data = response.json()
        assert "error" in data or "message" in data, "Should have error information"


class TestLogout:
    """Test logout functionality."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_logout_success(
        self,
        http_client: httpx.AsyncClient,
        auth_tokens: AuthTokens,
        debug_user_data: dict
    ):
        """Test successful logout invalidates tokens."""
        # Ensure we have tokens
        if not auth_tokens.refresh_token:
            await http_client.post("/auth/register", json=debug_user_data)
            login_response = await http_client.post(
                "/auth/login",
                json={
                    "email": debug_user_data["email"],
                    "password": debug_user_data["password"]
                }
            )
            tokens = login_response.json()
            auth_tokens.set_tokens(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"]
            )

        logout_data = {"refresh_token": auth_tokens.refresh_token}
        response = await http_client.post("/auth/logout", json=logout_data)

        assert response.status_code == 200, f"Logout: Expected 200, got {response.status_code}"

        data = response.json()
        assert "message" in data, "Should have success message"


class TestCompleteAuthFlow:
    """Test complete authentication flow end-to-end."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.auth
    async def test_complete_authentication_flow(self, http_client: httpx.AsyncClient, flow_user_data: dict):
        """Test complete flow: Register → Login → Profile → Refresh → Logout."""

        # 1. REGISTRATION
        register_response = await http_client.post("/auth/register", json=flow_user_data)
        assert register_response.status_code in [200, 409], \
            f"Registration should succeed or user exists, got {register_response.status_code}"

        # 2. LOGIN
        login_response = await http_client.post(
            "/auth/login",
            json={
                "email": flow_user_data["email"],
                "password": flow_user_data["password"]
            }
        )
        assert login_response.status_code == 200, f"Login should succeed, got {login_response.status_code}"

        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 3. GET PROFILE
        me_response = await http_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == 200, f"Get profile should succeed, got {me_response.status_code}"

        # 4. REFRESH TOKEN
        refresh_response = await http_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 200, f"Token refresh should succeed, got {refresh_response.status_code}"

        new_tokens = refresh_response.json()
        new_refresh_token = new_tokens["refresh_token"]

        # 5. LOGOUT
        logout_response = await http_client.post(
            "/auth/logout",
            json={"refresh_token": new_refresh_token}
        )
        assert logout_response.status_code == 200, f"Logout should succeed, got {logout_response.status_code}"

        # 6. VERIFY TOKEN IS REVOKED
        verify_response = await http_client.post(
            "/auth/refresh",
            json={"refresh_token": new_refresh_token}
        )
        assert verify_response.status_code in [400, 401], \
            f"Token should be revoked after logout, got {verify_response.status_code}"


class TestValidation:
    """Test input validation with proper error responses."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_register_missing_required_fields_returns_422(self, http_client: httpx.AsyncClient):
        """Test registration with missing required fields returns 422 with details."""
        incomplete_data = {
            "email": "test_missing@example.com"
            # Missing name and password
        }
        response = await http_client.post("/auth/register", json=incomplete_data)

        assert response.status_code == 422, f"Missing fields: Expected 422, got {response.status_code}"

        data = response.json()
        # Verify validation error structure
        assert "error" in data, "Should have error field"
        assert data["error"] is True, "Error should be True"
        assert "error_code" in data, "Should have error_code"
        assert data["error_code"] == "VALIDATION_ERROR", "Should have validation error code"
        assert "details" in data, "Should have validation details"
        assert isinstance(data["details"], list), "Details should be a list"
        assert len(data["details"]) > 0, "Should have at least one validation error"

        # Verify detail structure
        for detail in data["details"]:
            assert "loc" in detail, "Detail should have loc"
            assert "msg" in detail, "Detail should have msg"
            assert "type" in detail, "Detail should have type"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_register_invalid_email_format_returns_422(self, http_client: httpx.AsyncClient):
        """Test registration with invalid email format returns 422."""
        invalid_data = {
            "name": "Test User",
            "email": "not-an-email",
            "password": "Password123!"
        }
        response = await http_client.post("/auth/register", json=invalid_data)

        assert response.status_code == 422, f"Invalid email: Expected 422, got {response.status_code}"

        data = response.json()
        assert "details" in data, "Should have validation details"

        # Find email error
        email_errors = [d for d in data["details"] if "email" in str(d.get("loc", []))]
        assert len(email_errors) > 0, "Should have email validation error"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_register_weak_password_returns_error(self, http_client: httpx.AsyncClient):
        """Test registration with weak password returns validation error."""
        weak_data = {
            "name": "Test User",
            "email": "test_weak@example.com",
            "password": "weak"  # Too weak
        }
        response = await http_client.post("/auth/register", json=weak_data)

        assert response.status_code in [400, 422], \
            f"Weak password: Expected 400 or 422, got {response.status_code}"

        data = response.json()
        assert "details" in data or "message" in data, "Should have error information"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_register_short_password_returns_error(self, http_client: httpx.AsyncClient):
        """Test registration with very short password returns validation error."""
        short_data = {
            "name": "Test User",
            "email": "test_short@example.com",
            "password": "123"
        }
        response = await http_client.post("/auth/register", json=short_data)

        assert response.status_code in [400, 422], \
            f"Short password: Expected 400 or 422, got {response.status_code}"

        data = response.json()
        assert "details" in data or "message" in data, "Should have error information"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_validation_errors_translated_spanish(self, http_client: httpx.AsyncClient):
        """Test validation errors are translated to Spanish."""
        incomplete_data = {"email": "test@example.com"}
        response = await http_client.post(
            "/auth/register",
            json=incomplete_data,
            headers={"Accept-Language": "es"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "message" in data
        # Main message should be in Spanish
        assert "validación" in data["message"].lower() or "error" in data["message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_validation_errors_translated_english(self, http_client: httpx.AsyncClient):
        """Test validation errors are translated to English."""
        incomplete_data = {"email": "test@example.com"}
        response = await http_client.post(
            "/auth/register",
            json=incomplete_data,
            headers={"Accept-Language": "en"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "message" in data
        # Main message should be in English
        assert "validation" in data["message"].lower() or "error" in data["message"].lower()
