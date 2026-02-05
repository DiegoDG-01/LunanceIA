"""Unit tests for Bank entity."""

import pytest
from domain.entities.bank import Bank


@pytest.mark.unit
class TestBankEntity:
    """Test Bank entity creation and validation."""

    def test_create_bank_with_required_fields(self):
        """Test creating a bank with required fields only."""
        bank = Bank(id=1, name="BBVA", code="BBV")

        assert bank.id == 1
        assert bank.name == "BBVA"
        assert bank.code == "BBV"
        assert bank.country == "MX"  # default
        assert bank.logo_url is None
        assert bank.color is None
        assert bank.is_active is True  # default

    def test_create_bank_with_all_fields(self):
        """Test creating a bank with all fields."""
        bank = Bank(
            id=1,
            name="BBVA México",
            code="BBV",
            country="MX",
            logo_url="https://example.com/bbva-logo.png",
            color="#004481",
            is_active=True,
        )

        assert bank.id == 1
        assert bank.name == "BBVA México"
        assert bank.code == "BBV"
        assert bank.country == "MX"
        assert bank.logo_url == "https://example.com/bbva-logo.png"
        assert bank.color == "#004481"
        assert bank.is_active is True

    def test_create_bank_inactive(self):
        """Test creating an inactive bank."""
        bank = Bank(id=1, name="Old Bank", code="OLD", is_active=False)

        assert bank.is_active is False


@pytest.mark.unit
class TestBankCreateNew:
    """Test Bank.create_new factory method."""

    def test_create_new_with_required_fields(self):
        """Test create_new with required fields only."""
        bank = Bank.create_new(name="Santander", code="SAN")

        assert bank.id == 0  # Default for new entities
        assert bank.name == "Santander"
        assert bank.code == "SAN"
        assert bank.country == "MX"
        assert bank.is_active is True

    def test_create_new_with_all_fields(self):
        """Test create_new with all optional fields."""
        bank = Bank.create_new(
            name="Nu Bank",
            code="NU",
            country="MX",
            logo_url="https://example.com/nu-logo.png",
            color="#820AD1",
        )

        assert bank.name == "Nu Bank"
        assert bank.code == "NU"
        assert bank.country == "MX"
        assert bank.logo_url == "https://example.com/nu-logo.png"
        assert bank.color == "#820AD1"

    def test_create_new_strips_whitespace(self):
        """Test that create_new strips whitespace from name and code."""
        bank = Bank.create_new(name="  BBVA  ", code="  BBV  ")

        assert bank.name == "BBVA"
        assert bank.code == "BBV"

    def test_create_new_uppercase_country(self):
        """Test that create_new uppercases country code."""
        bank = Bank.create_new(name="Test Bank", code="TST", country="mx")

        assert bank.country == "MX"

    def test_create_new_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Bank name cannot be empty"):
            Bank.create_new(name="", code="TST")

    def test_create_new_whitespace_name_raises_error(self):
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="Bank name cannot be empty"):
            Bank.create_new(name="   ", code="TST")

    def test_create_new_empty_code_raises_error(self):
        """Test that empty code raises ValueError."""
        with pytest.raises(ValueError, match="Bank code cannot be empty"):
            Bank.create_new(name="Test Bank", code="")

    def test_create_new_whitespace_code_raises_error(self):
        """Test that whitespace-only code raises ValueError."""
        with pytest.raises(ValueError, match="Bank code cannot be empty"):
            Bank.create_new(name="Test Bank", code="   ")
