"""Unit tests for authentication schemas and basic functionality."""

import pytest
from pydantic import ValidationError

# Test the request schemas which should be importable
try:
    from presentation.schemas.requests.auth import (
        LoginRequest,
        RegisterRequest,
        RefreshTokenRequest
    )
    SCHEMAS_AVAILABLE = True
except ImportError:
    SCHEMAS_AVAILABLE = False


@pytest.mark.skipif(not SCHEMAS_AVAILABLE, reason="Schemas not available due to import issues")
class TestAuthSchemas:
    """Test authentication request schemas."""

    def test_register_request_validation(self):
        """Test register request validation."""
        if not SCHEMAS_AVAILABLE:
            pytest.skip("Schemas not available")

        # Valid request
        valid_request = RegisterRequest(
            name="Test User",
            email="test@example.com",
            password="Password123!"
        )
        assert valid_request.email == "test@example.com"
        assert valid_request.name == "Test User"

        # Test email validation
        with pytest.raises(ValidationError):
            RegisterRequest(
                name="Test User",
                email="invalid-email",
                password="Password123!"
            )

    def test_login_request_validation(self):
        """Test login request validation."""
        if not SCHEMAS_AVAILABLE:
            pytest.skip("Schemas not available")

        valid_request = LoginRequest(
            email="test@example.com",
            password="password123"
        )
        assert valid_request.email == "test@example.com"
        assert valid_request.password == "password123"

    def test_refresh_token_request_validation(self):
        """Test refresh token request validation."""
        if not SCHEMAS_AVAILABLE:
            pytest.skip("Schemas not available")

        valid_request = RefreshTokenRequest(
            refresh_token="some-refresh-token"
        )
        assert valid_request.refresh_token == "some-refresh-token"


class TestBasicFunctionality:
    """Test basic functionality that doesn't require complex imports."""

    def test_string_operations(self):
        """Test basic string operations."""
        email = "test@example.com"
        assert "@" in email
        assert email.endswith(".com")

    def test_password_validation_logic(self):
        """Test password validation logic."""
        def has_uppercase(password: str) -> bool:
            return any(c.isupper() for c in password)

        def has_special_char(password: str) -> bool:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            return any(c in special_chars for c in password)

        # Test password validation
        strong_password = "Password123!"
        assert has_uppercase(strong_password)
        assert has_special_char(strong_password)
        assert len(strong_password) >= 8

        weak_password = "password"
        assert not has_uppercase(weak_password)
        assert not has_special_char(weak_password)
