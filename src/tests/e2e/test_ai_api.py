"""End-to-end tests for AI API endpoints.

Los casos de éxito dependen de servicios externos de LLM, por lo que aquí
solo se cubre el contrato de autenticación de los endpoints.
"""

import pytest
import httpx


@pytest.mark.e2e
class TestAIEndpointsAuth:
    @pytest.mark.asyncio
    async def test_expense_advisor_unauthorized(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/ai/expense_advisor")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_analyze_image_unauthorized(self, http_client: httpx.AsyncClient):
        response = await http_client.post(
            "/ai/analyze/image", files={"file": ("ticket.jpg", b"fake-bytes", "image/jpeg")}
        )
        assert response.status_code == 401
