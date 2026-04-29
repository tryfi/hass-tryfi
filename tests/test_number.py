"""Test TryFi sensor platform."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.tryfi.number import TryFiPetWeightNumber

from syrupy.assertion import SnapshotAssertion


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock()
    coordinator.data = Mock()
    return coordinator


@pytest.fixture
def mock_pet_with_stats():
    """Create a mock pet with statistics."""
    pet = Mock()
    pet.petId = "test_pet_123"
    pet.name = "Fido"
    pet.photoLink = "https://example.com/photo.jpg"
    pet.activityType = "REST"
    pet.currPlaceName = "Home"
    pet.currPlaceAddress = "123 Main St"
    pet.device = Mock()
    pet.device.batteryPercent = 75
    pet.device.isCharging = False
    pet.device.connectedTo = "Cellular"
    pet.device.connectionState = "ConnectedToCellular"
    pet.dailySteps = 5000
    pet.weeklyTotalDistance = 17500
    pet.monthlySleep = 864000
    return pet


async def test_weight_number(
    hass: HomeAssistant,
    mock_coordinator,
    mock_pet_with_stats,
    snapshot: SnapshotAssertion,
) -> None:
    """Test TryFi battery sensor."""
    mock_coordinator.data.getPet.return_value = mock_pet_with_stats

    sensor = TryFiPetWeightNumber(mock_coordinator, mock_pet_with_stats)

    assert sensor.native_unit_of_measurement == "kg"
