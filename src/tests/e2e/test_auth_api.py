"""End-to-end tests for auth API endpoints."""

import uuid

import pytest
import httpx

from tests.email_flow import PASSWORD, last_email_to, signup, token_from, unique_email

# Cada test usa un dispositivo web (sin X-Lunance-Client = web).
DEVICE = {"X-Lunance-Device": str(uuid.uuid4())}


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


async def _account(http_client: httpx.AsyncClient) -> str:
    return await signup(http_client, http_client.outbox)  # type: ignore[attr-defined]


async def _login(http_client: httpx.AsyncClient, email: str, password: str = PASSWORD):
    return await http_client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=DEVICE,
    )


class TestRegister:
    """Test POST /auth/register + POST /auth/email/verify."""

    @pytest.mark.asyncio
    async def test_register_accepts_and_sends_verification(
        self, http_client: httpx.AsyncClient
    ):
        email = unique_email("newuser")
        response = await http_client.post(
            "/auth/register",
            json={"email": email, "username": "newuser_e2e", "password": PASSWORD},
        )

        assert response.status_code == 202
        assert set(response.json()) == {"message"}
        token = token_from(last_email_to(http_client.outbox, email))  # type: ignore[attr-defined]

        verified = await http_client.post("/auth/email/verify", json={"token": token})

        assert verified.status_code == 200
        data = verified.json()
        assert set(data) == {"user_uuid", "username", "email", "message"}
        assert data["username"] == "newuser_e2e"
        assert data["email"] == email

    @pytest.mark.asyncio
    async def test_login_is_not_possible_before_verifying(
        self, http_client: httpx.AsyncClient
    ):
        email = unique_email("pending")
        await http_client.post(
            "/auth/register",
            json={"email": email, "username": "pending_e2e", "password": PASSWORD},
        )

        response = await _login(http_client, email)

        assert response.status_code == 403
        assert response.json()["error_code"] == "AUTH_EMAIL_NOT_VERIFIED"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, http_client: httpx.AsyncClient):
        await signup(http_client, http_client.outbox, username="duplicate_user")  # type: ignore[attr-defined]

        response = await http_client.post(
            "/auth/register",
            json={
                "email": unique_email(),
                "username": "duplicate_user",
                "password": PASSWORD,
            },
        )

        assert response.status_code == 409
        assert response.json()["error_code"] == "BUSINESS_USERNAME_EXISTS"

    @pytest.mark.asyncio
    async def test_register_short_password(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/register",
            json={"email": unique_email(), "username": "shortpw", "password": "short"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/register",
            json={
                "email": unique_email(),
                "username": "weakpw",
                "password": "weakpassword",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_empty_username(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/register",
            json={"email": unique_email(), "username": "", "password": PASSWORD},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/register",
            json={"email": "not-an-email", "username": "x", "password": PASSWORD},
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
        email = await _account(http_client)

        response = await _login(http_client, email.upper())

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert set(data.keys()) == {"access_token", "token_type", "expires_in"}
        assert isinstance(data["expires_in"], int) and data["expires_in"] > 0
        assert isinstance(data["access_token"], str)
        assert "refresh_token" in response.cookies
        assert isinstance(response.cookies["refresh_token"], str)

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, http_client: httpx.AsyncClient):
        response = await _login(http_client, "nonexistent_user@example.com")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, http_client: httpx.AsyncClient):
        email = await _account(http_client)

        response = await _login(http_client, email, "WrongPassword1!")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_with_username_is_rejected(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/login",
            json={"username": "someone", "password": PASSWORD},
            headers=DEVICE,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_empty_fields(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/auth/login",
            json={"email": "", "password": ""},
            headers=DEVICE,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_fields(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/auth/login", json={}, headers=DEVICE)

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
        assert set(data.keys()) == {
            "user_uuid",
            "username",
            "email",
            "email_verified",
            "is_active",
        }
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
        email = await _account(http_client)
        login_response = await _login(http_client, email)
        old_token = _reforward_refresh_cookie(http_client, login_response)

        response = await http_client.post("/auth/refresh", headers=DEVICE)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert isinstance(data["access_token"], str)
        assert "refresh_token" in response.cookies
        assert response.cookies["refresh_token"].startswith("rt_")
        assert response.cookies["refresh_token"] != old_token
        assert "refresh_token" not in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, http_client: httpx.AsyncClient):
        http_client.cookies.set("refresh_token", "not-a-valid-refresh-token")

        response = await http_client.post("/auth/refresh", headers=DEVICE)

        assert response.status_code == 401
        assert response.json()["error_code"] == "AUTH_SESSION_EXPIRED"

    @pytest.mark.asyncio
    async def test_refresh_missing_token(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/auth/refresh", headers=DEVICE)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_missing_device_header(self, http_client: httpx.AsyncClient):
        http_client.cookies.set("refresh_token", "rt_whatever")

        response = await http_client.post("/auth/refresh")

        assert response.status_code == 422


class TestLogout:
    """Test POST /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success_revokes_refresh_token(
        self, http_client: httpx.AsyncClient
    ):
        email = await _account(http_client)
        login_response = await _login(http_client, email)
        _reforward_refresh_cookie(http_client, login_response)

        response = await http_client.post("/auth/logout")

        assert response.status_code == 200
        assert response.json() == {"message": "Logout exitoso"}

        # The revoked refresh token must no longer be usable.
        refresh_response = await http_client.post("/auth/refresh", headers=DEVICE)
        assert refresh_response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_missing_token(self, http_client: httpx.AsyncClient):
        response = await http_client.post("/auth/logout")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_empty_token(self, http_client: httpx.AsyncClient):
        http_client.cookies.set("refresh_token", "")

        response = await http_client.post("/auth/logout")

        assert response.status_code == 401
