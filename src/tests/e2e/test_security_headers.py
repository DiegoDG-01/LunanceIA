"""Tests E2E para las cabeceras de seguridad HTTP (hallazgo A3 del security review)."""

import pytest


@pytest.mark.asyncio
class TestSecurityHeaders:
    async def test_security_headers_present_on_api_responses(self, http_client):
        response = await http_client.get("http://test/")

        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Cache-Control"] == "no-store"
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers

    async def test_security_headers_present_on_error_responses(self, http_client):
        response = await http_client.get("http://test/api/v2/no-such-route")

        assert response.status_code == 404
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    async def test_docs_exempt_from_csp_only(self, http_client):
        """Swagger UI necesita CDN/inline; el resto de cabeceras debe mantenerse."""
        response = await http_client.get("http://test/docs")

        assert response.status_code == 200
        assert "Content-Security-Policy" not in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "Strict-Transport-Security" in response.headers
