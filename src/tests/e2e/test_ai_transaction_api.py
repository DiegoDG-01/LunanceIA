"""End-to-end tests for AI-powered transaction extraction."""

import pytest
import httpx
import io
from ..conftest import AuthTokens

@pytest.mark.e2e
class TestAITransactionAPI:
    """Test transaction creation via image processing (Gemini)."""

    @pytest.mark.asyncio
    async def test_create_transaction_from_image_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test scanning a receipt image and creating a transaction."""

        # 1. Create a test account
        account_data = {
            "name": "AI Test Account",
            "account_type": "CHECKING",
            "bank": "AI Bank",
            "initial_balance": 1000.00,
            "currency": "MXN"
        }
        acc_res = await http_client.post("/account", json=account_data, headers=auth_tokens.get_auth_headers())
        account_uuid = acc_res.json()["account_uuid"]

        # 2. Upload "image"
        # Create a real minimal image to pass PIL validation
        from PIL import Image
        img = Image.new('RGB', (10, 10), color='white')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)

        files = {"file": ("receipt.jpg", img_byte_arr, "image/jpeg")}
        data = {"account_uuid": account_uuid}

        response = await http_client.post(
            "/transaction/image",
            files=files,
            data=data,
            headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200
        result = response.json()

        # 3. Verify extracted data (matches MockGeminiService in conftest.py)
        assert result["description"] == "Mocked receipt description"
        assert float(result["amount"]) == 450.00
        assert result["transaction_type"] == "EXPENSE"

        # 4. Verify Account Balance Impact
        acc_check = await http_client.get(f"/account/{account_uuid}", headers=auth_tokens.get_auth_headers())
        # 1000 - 450 = 550
        assert float(acc_check.json()["current_balance"]) == 550.00

    @pytest.mark.asyncio
    async def test_ai_image_upload_unauthorized(self, http_client: httpx.AsyncClient):
        """Test AI image upload without authentication."""
        fake_image = io.BytesIO(b"content")
        files = {"file": ("receipt.jpg", fake_image, "image/jpeg")}
        data = {"account_uuid": "some-uuid"}

        response = await http_client.post("/transaction/image", files=files, data=data)
        assert response.status_code == 401
