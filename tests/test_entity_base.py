"""Test base entity functionality."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.tryfi.binary_sensor import TryFiBatteryChargingBinarySensor
from custom_components.tryfi.device_tracker import TryFiPetTracker
from custom_components.tryfi.light import TryFiPetLight
from custom_components.tryfi.select import TryFiLostModeSelect
from custom_components.tryfi.sensor import (
    PetGenericSensor,
    PetStatsSensor,
    TryFiBaseSensor,
    TryFiBatterySensor,
)


@pytest.fixture
def mock_coordinator():
    """Create a base mock coordinator."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.getPet = Mock(return_value=None)
    coordinator.data.getBase = Mock(return_value=None)
    return coordinator


@pytest.fixture
def mock_pet_minimal():
    """Create a minimal pet with only required attributes."""
    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test Pet"
    pet.device = Mock()
    pet.device.availableLedColors = []
    return pet


@pytest.fixture
def mock_base_minimal():
    """Create a minimal base with only required attributes."""
    base = Mock()
    base.baseId = "test_base"
    base.name = "Test Base"
    base.online = False
    base.device = Mock()
    base.device.availableLedColors.return_value = []
    return base


async def test_entity_device_info_variations(
    hass: HomeAssistant, mock_coordinator
) -> None:
    """Test device_info with various data states."""
    # Test with minimal pet data
    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test"
    # No breed, no device

    mock_coordinator.data.getPet.return_value = pet

    sensor = TryFiBatterySensor(mock_coordinator, pet)
    device_info = sensor.device_info

    assert device_info["identifiers"] == {("tryfi", "test_pet")}
    assert device_info["name"] == "Test"
    assert device_info["manufacturer"] == "TryFi"
    assert device_info["model"] == "Smart Dog Collar"
    assert "sw_version" not in device_info

    # Add breed
    pet.breed = "Poodle"
    device_info = sensor.device_info
    assert device_info["model"] == "Smart Dog Collar"


async def test_sensor_icon_selection(hass: HomeAssistant, mock_coordinator) -> None:
    """Test icon selection for different sensor types."""
    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test"

    mock_coordinator.data.getPet.return_value = pet

    # Test generic sensor icons
    sensor_types_icons = {
        "Activity Type": "mdi:run",
        "Current Place Name": "mdi:map-marker",
        "Current Place Address": "mdi:home-map-marker",
        "Connected To": "mdi:wifi",
        "Unknown Type": "mdi:information",  # Default
    }

    for sensor_type, expected_icon in sensor_types_icons.items():
        sensor = PetGenericSensor(mock_coordinator, pet, sensor_type)
        assert sensor._attr_icon == expected_icon


async def test_stats_sensor_attributes(hass: HomeAssistant, mock_coordinator) -> None:
    """Test stats sensor attribute assignment."""
    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test"

    mock_coordinator.data.getPet.return_value = pet

    # Test different stat types
    sensor = PetStatsSensor(mock_coordinator, pet, "DISTANCE", "WEEKLY")
    assert sensor._attr_name == "Test Weekly Distance"
    assert sensor._attr_unique_id == "test_pet-weekly-distance"
    assert hasattr(sensor, "_attr_native_unit_of_measurement")

    # Test with invalid stat type
    sensor = PetStatsSensor(mock_coordinator, pet, "INVALID", "DAILY")
    assert not hasattr(sensor, "_attr_device_class")


async def test_base_sensor_states(hass: HomeAssistant, mock_coordinator) -> None:
    """Test base sensor online/offline states."""
    base = Mock()
    base.baseId = "test_base"
    base.name = "Test Base"
    base.online = True

    mock_coordinator.data.getBase.return_value = base

    sensor = TryFiBaseSensor(mock_coordinator, base)
    assert sensor.native_value == "Online"

    base.online = False
    assert sensor.native_value == "Offline"

    # Test with None
    mock_coordinator.data.getBase.return_value = None
    assert sensor.native_value is None


async def test_entity_unique_id_format(
    hass: HomeAssistant, mock_coordinator, mock_pet_minimal
) -> None:
    """Test unique ID formatting across entity types."""
    expected_formats = {
        TryFiBatterySensor: "test_pet-battery",
        TryFiPetTracker: "test_pet-tracker",
        TryFiBatteryChargingBinarySensor: "test_pet-battery-charging",
        TryFiPetLight: "test_pet-light",
        TryFiLostModeSelect: "test_pet-lost",
    }

    for entity_class, expected_id in expected_formats.items():
        entity = entity_class(mock_coordinator, mock_pet_minimal)
        assert entity.unique_id == expected_id or entity._attr_unique_id == expected_id
