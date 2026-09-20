"""End-to-end tests for auth API endpoints."""

import pytest
import httpx


def _reforward_refresh_cookie(client: httpx.AsyncClient, response: httpx.Response) -> str:
    """Re-set the refresh cookie without the Secure flag.

    The server marks it Secure, and httpx's cookie jar refuses to resend a
    Secure cookie over the plain-http ASGI test transport, so the next request
    in the same test would otherwise arrive with no cookie at all.
    """
    token = response.cookies.get("refresh_token")
    assert token, "expected Set-Cookie refresh_token in response"
    client.cookies.set("refresh_token", token)
    return token


class TestRegister:
    """Test POST /auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/register",
            json={"username": "newuser_e2e", "password": "Password123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "user_uuid" in data
        assert data["username"] == "newuser_e2e"
        assert "message" in data
        assert set(data.keys()) == {"user_uuid", "username", "message"}
        assert isinstance(data["user_uuid"], str)

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, http_client: httpx.AsyncClient):
        await http_client.post(
            "/auth/register",
            json={"username": "duplicate_user", "password": "Password123!"},
        )

        response = await http_client.post(
            "/auth/register",
            json={"username": "duplicate_user", "password": "Password123!"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_short_password(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/register",
            json={"username": "shortpwuser", "password": "short"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_empty_username(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/register",
            json={"username": "", "password": "Password123!"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/auth/register", json={})

        assert response.status_code == 422


class TestLogin:
    """Test POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, http_client: httpx.AsyncClient):
        # Register first
        await http_client.post(
            "/auth/register",
            json={"username": "loginuser_e2e", "password": "Password123!"},
        )

        response = await http_client.post(
            "/auth/login",
            json={"username": "loginuser_e2e", "password": "Password123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert set(data.keys()) == {"access_token", "token_type"}
        assert isinstance(data["access_token"], str)
        assert "refresh_token" in response.cookies
        assert isinstance(response.cookies["refresh_token"], str)

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/login",
            json={"username": "nonexistent_user", "password": "Password123!"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, http_client: httpx.AsyncClient):
        await http_client.post(
            "/auth/register",
            json={"username": "wrongpwuser_e2e", "password": "Password123!"},
        )

        response = await http_client.post(
            "/auth/login",
            json={"username": "wrongpwuser_e2e", "password": "WrongPassword1!"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_empty_fields(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/login",
            json={"username": "", "password": ""},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_fields(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/auth/login", json={})

        assert response.status_code == 422


class TestMe:
    """Test GET /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_me_success(self, http_client: httpx.AsyncClient):
        response = await http_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer mock-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"user_uuid", "username", "is_active"}
        assert isinstance(data["user_uuid"], str)
        assert isinstance(data["username"], str)
        assert isinstance(data["is_active"], bool)

    @pytest.mark.asyncio
    async def test_me_no_token(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, http_client: httpx.AsyncClient):
        response = await http_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


class TestRefreshToken:
    """Test POST /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success_returns_new_tokens(self, http_client: httpx.AsyncClient):
        await http_client.post(
            "/auth/register",
            json={"username": "refreshuser_e2e", "password": "Password123!"},
        )
        login_response = await http_client.post(
            "/auth/login",
            json={"username": "refreshuser_e2e", "password": "Password123!"},
        )
        _reforward_refresh_cookie(http_client, login_response)

        response = await http_client.post("/auth/refresh")

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert isinstance(data["access_token"], str)
        assert "refresh_token" in response.cookies
        assert isinstance(response.cookies["refresh_token"], str)

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, http_client: httpx.AsyncClient):
        http_client.cookies.set("refresh_token", "not-a-valid-refresh-token")

        response = await http_client.post("/auth/refresh")

        assert response.status_code in [400, 401]

    @pytest.mark.asyncio
    async def test_refresh_missing_token(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/auth/refresh")

        assert response.status_code == 401


class TestLogout:
    """Test POST /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success_revokes_refresh_token(
        self, http_client: httpx.AsyncClient
    ):
        await http_client.post(
            "/auth/register",
            json={"username": "logoutuser_e2e", "password": "Password123!"},
        )
        login_response = await http_client.post(
            "/auth/login",
            json={"username": "logoutuser_e2e", "password": "Password123!"},
        )
        _reforward_refresh_cookie(http_client, login_response)

        response = await http_client.post("/auth/logout")

        assert response.status_code == 200
        assert response.json() == {"message": "Logout exitoso"}

        # The revoked refresh token must no longer be usable.
        refresh_response = await http_client.post("/auth/refresh")
        assert refresh_response.status_code in [400, 401]

    @pytest.mark.asyncio
    async def test_logout_missing_token(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/auth/logout")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_empty_token(self, http_client: httpx.AsyncClient):
        http_client.cookies.set("refresh_token", "")

        response = await http_client.post("/auth/logout")

        assert response.status_code == 401
