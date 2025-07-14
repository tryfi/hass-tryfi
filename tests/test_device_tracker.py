"""Test TryFi device tracker platform."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from homeassistant.components.device_tracker import SourceType
from homeassistant.core import HomeAssistant

from custom_components.tryfi.const import DOMAIN
from custom_components.tryfi.device_tracker import TryFiPetTracker


@pytest.fixture
def mock_pet_location():
    """Create a mock pet with location data."""
    pet = Mock()
    pet.petId = "test_pet_123"
    pet.name = "Fido"
    pet.photoLink = "https://example.com/photo.jpg"
    pet.currLatitude = 40.7128
    pet.currLongitude = -74.0060
    pet.breed = "Labrador"
    pet.device = Mock()
    pet.device.batteryPercent = 85
    pet.device.buildId = "1.2.3"
    return pet


@pytest.fixture
def mock_coordinator_tracker(mock_pet_location):
    """Create a mock coordinator for tracker tests."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.getPet = Mock(return_value=mock_pet_location)
    return coordinator


async def test_tracker_entity_properties(
    hass: HomeAssistant, mock_coordinator_tracker, mock_pet_location
) -> None:
    """Test TryFi tracker entity properties."""
    tracker = TryFiPetTracker(mock_coordinator_tracker, mock_pet_location)

    assert tracker._attr_unique_id == "test_pet_123-tracker"
    assert tracker._attr_name == "Fido Tracker"
    assert tracker.entity_picture == "https://example.com/photo.jpg"
    assert tracker.latitude == 40.7128
    assert tracker.longitude == -74.0060
    assert tracker.source_type == SourceType.GPS
    assert tracker.battery_level == 85

    device_info = tracker.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_pet_123")}
    assert device_info["name"] == "Fido"
    assert "Labrador" in device_info["model"]
    assert device_info["sw_version"] == "1.2.3"


async def test_tracker_no_pet_data(
    hass: HomeAssistant, mock_coordinator_tracker
) -> None:
    """Test tracker when pet data is not available."""
    mock_coordinator_tracker.data.getPet.return_value = None

    mock_pet = Mock()
    mock_pet.petId = "test_pet"
    mock_pet.name = "Test"

    tracker = TryFiPetTracker(mock_coordinator_tracker, mock_pet)

    assert tracker.entity_picture is None
    assert tracker.latitude is None
    assert tracker.longitude is None
    assert tracker.battery_level is None
    assert tracker.device_info == {}


async def test_tracker_missing_attributes(
    hass: HomeAssistant, mock_coordinator_tracker
) -> None:
    """Test tracker with missing pet attributes."""
    pet = Mock()
    pet.petId = "test_pet_123"
    pet.name = "Fido"
    pet.photoLink = None
    pet.currLatitude = None
    pet.currLongitude = None
    pet.breed = "Breed"
    pet.device = Mock()
    pet.device.batteryPercent = None
    pet.device.buildId = None
    # No other attributes

    mock_coordinator_tracker.data.getPet.return_value = pet

    tracker = TryFiPetTracker(mock_coordinator_tracker, pet)

    # Should handle missing attributes gracefully
    assert tracker.entity_picture is None
    assert tracker.latitude is None
    assert tracker.longitude is None
    assert tracker.battery_level is None

    device_info = tracker.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_pet_123")}
    assert device_info["name"] == "Fido"
    assert "sw_version" not in device_info


async def test_tracker_partial_device_data(
    hass: HomeAssistant, mock_coordinator_tracker, mock_pet_location
) -> None:
    """Test tracker with partial device data."""
    # Remove device
    mock_pet_location.device = None

    tracker = TryFiPetTracker(mock_coordinator_tracker, mock_pet_location)

    assert tracker.battery_level is None
    assert "sw_version" not in tracker.device_info

    # Add device without battery
    mock_pet_location.device = Mock(spec=[])
    assert tracker.battery_level is None
