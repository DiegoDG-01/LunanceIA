"""Unit tests for authentication schemas."""

import pytest
from pydantic import ValidationError

from presentation.schemas.requests.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
)


@pytest.mark.unit
class TestAuthSchemas:
    """Test authentication request schemas."""

    def test_register_request_valid(self):
        request = RegisterRequest(username="testuser", password="Password123!")
        assert request.username == "testuser"
        assert request.password == "Password123!"

    def test_register_request_empty_username(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="", password="Password123!")

    def test_register_request_short_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", password="short")

    def test_login_request_valid(self):
        request = LoginRequest(username="testuser", password="Password123!")
        assert request.username == "testuser"
        assert request.password == "Password123!"

    def test_login_request_empty_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="Password123!")

    def test_login_request_short_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="testuser", password="short")

    def test_refresh_token_request_valid(self):
        request = RefreshTokenRequest(refresh_token="some-refresh-token")
        assert request.refresh_token == "some-refresh-token"

    def test_refresh_token_request_missing(self):
        with pytest.raises(ValidationError):
            RefreshTokenRequest()  # type: ignore[call-arg]
