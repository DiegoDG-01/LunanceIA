"""End-to-end tests for auth API endpoints."""

import pytest
import httpx


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
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert set(data.keys()) == {"access_token", "refresh_token", "token_type"}
        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)

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


class TestLogout:
    """Test POST /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_missing_token(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/auth/logout", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_logout_empty_token(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/logout",
            json={"refresh_token": ""},
        )

        assert response.status_code == 400
