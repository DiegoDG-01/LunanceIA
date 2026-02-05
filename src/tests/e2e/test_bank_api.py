"""End-to-end tests for bank API endpoints."""

import pytest
import httpx


class TestGetBanks:
    """Test GET /bank endpoint."""

    @pytest.mark.asyncio
    async def test_get_banks_success(self, http_client: httpx.AsyncClient):
        """Test successful retrieval of banks list."""
        response = await http_client.get("/bank/")

        assert response.status_code == 200

        data = response.json()
        assert "banks" in data
        assert "total" in data
        assert isinstance(data["banks"], list)
        assert isinstance(data["total"], int)
        assert data["total"] == len(data["banks"])

    @pytest.mark.asyncio
    async def test_get_banks_returns_bank_structure(self, http_client: httpx.AsyncClient):
        """Test that banks have the expected structure."""
        response = await http_client.get("/bank/")

        assert response.status_code == 200

        data = response.json()

        # If there are banks, check their structure
        if data["banks"]:
            bank = data["banks"][0]
            assert "id" in bank
            assert "name" in bank
            assert "code" in bank
            assert "country" in bank
            assert "is_active" in bank
            # Optional fields
            assert "logo_url" in bank
            assert "color" in bank

    @pytest.mark.asyncio
    async def test_get_banks_only_active_true(self, http_client: httpx.AsyncClient):
        """Test that only_active=true returns only active banks."""
        response = await http_client.get("/bank/", params={"only_active": True})

        assert response.status_code == 200

        data = response.json()

        # All returned banks should be active
        for bank in data["banks"]:
            assert bank["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_banks_only_active_false(self, http_client: httpx.AsyncClient):
        """Test that only_active=false returns all banks."""
        response = await http_client.get("/bank/", params={"only_active": False})

        assert response.status_code == 200

        data = response.json()
        assert "banks" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_banks_default_only_active(self, http_client: httpx.AsyncClient):
        """Test that default behavior is only_active=true."""
        # Request without param
        response_default = await http_client.get("/bank/")
        # Request with explicit only_active=true
        response_explicit = await http_client.get("/bank/", params={"only_active": True})

        assert response_default.status_code == 200
        assert response_explicit.status_code == 200

        data_default = response_default.json()
        data_explicit = response_explicit.json()

        # Both should return same results
        assert data_default["total"] == data_explicit["total"]


class TestBankResponseFormat:
    """Test bank API response format."""

    @pytest.mark.asyncio
    async def test_bank_list_response_format(self, http_client: httpx.AsyncClient):
        """Test that bank list response follows expected format."""
        response = await http_client.get("/bank/")

        assert response.status_code == 200

        data = response.json()

        # Check response structure
        assert isinstance(data, dict)
        assert set(data.keys()) == {"banks", "total"}

    @pytest.mark.asyncio
    async def test_bank_fields_types(self, http_client: httpx.AsyncClient):
        """Test that bank fields have correct types."""
        response = await http_client.get("/bank/")

        assert response.status_code == 200

        data = response.json()

        for bank in data["banks"]:
            assert isinstance(bank["id"], int)
            assert isinstance(bank["name"], str)
            assert isinstance(bank["code"], str)
            assert isinstance(bank["country"], str)
            assert isinstance(bank["is_active"], bool)
            # Optional fields can be None or string
            assert bank["logo_url"] is None or isinstance(bank["logo_url"], str)
            assert bank["color"] is None or isinstance(bank["color"], str)
