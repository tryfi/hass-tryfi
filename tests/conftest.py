"""Global fixtures for TryFi integration tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override setup entry."""
    with patch(
        "custom_components.tryfi.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_pet():
    """Create a mock pet."""
    pet = Mock()
    pet.petId = "test_pet_id"
    pet.name = "Test Dog"
    pet.device = Mock()
    pet.device.moduleId = "test_module_id"
    pet.device.batteryPercent = 85
    pet.device.isCharging = False
    pet.device.ledOn = True
    pet.device.ledColorCode = 3
    pet.device.connectionState = "CONNECTED"
    pet.currLongitude = -74.123456
    pet.currLatitude = 40.123456
    pet.lastUpdated = "2023-01-01T00:00:00Z"
    pet.activityType = "REST"
    pet.currentPlaceName = "Home"
    pet.currentPlaceAddress = "123 Main St"
    pet.stats = {
        "DAILY": {"STEPS": 1000, "DISTANCE": 0.5, "SLEEP": 480, "NAP": 120},
        "WEEKLY": {"STEPS": 7000, "DISTANCE": 3.5, "SLEEP": 3360, "NAP": 840},
        "MONTHLY": {"STEPS": 30000, "DISTANCE": 15, "SLEEP": 14400, "NAP": 3600},
    }
    pet.isLost = False
    return pet


@pytest.fixture
def mock_base():
    """Create a mock base."""
    base = Mock()
    base.baseId = "test_base_id"
    base.name = "Test Base"
    base.online = True
    return base