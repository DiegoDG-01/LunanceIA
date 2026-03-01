"""Unit tests for GetBanksHandler."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from application.banks.queries.get_banks import GetBanksQuery, GetBanksHandler
from domain.entities.bank import Bank


@pytest.mark.unit
class TestGetBanksHandler:
    """Test GetBanksHandler query handler."""

    @pytest.fixture
    def mock_bank_repo(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_bank_repo):
        return GetBanksHandler(bank_repository=mock_bank_repo)

    @pytest.fixture
    def sample_banks(self):
        return [
            Bank(id=1, name="BBVA", code="BBV", country="MX", is_active=True),
            Bank(id=2, name="Santander", code="SAN", country="MX", is_active=True),
            Bank(id=3, name="Old Bank", code="OLD", country="MX", is_active=False),
        ]

    @pytest.mark.asyncio
    async def test_handle_returns_all_active_banks_by_default(
        self, handler, mock_bank_repo, sample_banks
    ):
        """Test that handler returns only active banks by default."""
        mock_bank_repo.get_all = AsyncMock(return_value=sample_banks)

        query = GetBanksQuery()
        result = await handler.handle(query)

        assert len(result) == 2
        assert all(bank.is_active for bank in result)
        mock_bank_repo.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_returns_all_banks_when_only_active_false(
        self, handler, mock_bank_repo, sample_banks
    ):
        """Test that handler returns all banks when only_active is False."""
        mock_bank_repo.get_all = AsyncMock(return_value=sample_banks)

        query = GetBanksQuery(only_active=False)
        result = await handler.handle(query)

        assert len(result) == 3
        mock_bank_repo.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_returns_empty_list_when_no_banks(
        self, handler, mock_bank_repo
    ):
        """Test that handler returns empty list when no banks exist."""
        mock_bank_repo.get_all = AsyncMock(return_value=[])

        query = GetBanksQuery()
        result = await handler.handle(query)

        assert len(result) == 0
        assert result == []

    @pytest.mark.asyncio
    async def test_handle_returns_bank_response_dtos(
        self, handler, mock_bank_repo, sample_banks
    ):
        """Test that handler returns BankResponseDTO objects."""
        mock_bank_repo.get_all = AsyncMock(return_value=sample_banks)

        query = GetBanksQuery()
        result = await handler.handle(query)

        # Check that results are DTOs with expected attributes
        for dto in result:
            assert hasattr(dto, "id")
            assert hasattr(dto, "name")
            assert hasattr(dto, "code")
            assert hasattr(dto, "country")
            assert hasattr(dto, "is_active")

    @pytest.mark.asyncio
    async def test_handle_preserves_bank_data(self, handler, mock_bank_repo):
        """Test that handler preserves all bank data in DTOs."""
        bank = Bank(
            id=1,
            name="BBVA México",
            code="BBV",
            country="MX",
            logo_url="https://example.com/logo.png",
            color="#004481",
            is_active=True,
        )
        mock_bank_repo.get_all = AsyncMock(return_value=[bank])

        query = GetBanksQuery()
        result = await handler.handle(query)

        assert len(result) == 1
        dto = result[0]
        assert dto.id == 1
        assert dto.name == "BBVA México"
        assert dto.code == "BBV"
        assert dto.country == "MX"
        assert dto.logo_url == "https://example.com/logo.png"
        assert dto.color == "#004481"
        assert dto.is_active is True


@pytest.mark.unit
class TestGetBanksQuery:
    """Test GetBanksQuery dataclass."""

    def test_default_values(self):
        """Test that GetBanksQuery has correct default values."""
        query = GetBanksQuery()

        assert query.only_active is True
        assert query.country is None

    def test_custom_values(self):
        """Test that GetBanksQuery accepts custom values."""
        query = GetBanksQuery(only_active=False, country="US")

        assert query.only_active is False
        assert query.country == "US"
