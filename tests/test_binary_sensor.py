"""Test TryFi binary sensor platform."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant

from custom_components.tryfi.binary_sensor import TryFiBatteryChargingBinarySensor
from custom_components.tryfi.const import DOMAIN


@pytest.fixture
def mock_pet_charging():
    """Create a mock pet with charging data."""
    pet = Mock()
    pet.petId = "test_pet_123"
    pet.name = "Fido"
    pet.breed = "Labrador"
    pet.device = Mock()
    pet.device.isCharging = True
    pet.device.buildId = "1.2.3"
    return pet


@pytest.fixture
def mock_coordinator_binary(mock_pet_charging):
    """Create a mock coordinator for binary sensor tests."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.getPet = Mock(return_value=mock_pet_charging)
    return coordinator


async def test_battery_charging_sensor_on(
    hass: HomeAssistant, mock_coordinator_binary, mock_pet_charging
) -> None:
    """Test battery charging sensor when charging."""
    sensor = TryFiBatteryChargingBinarySensor(
        mock_coordinator_binary, mock_pet_charging
    )

    assert sensor._attr_unique_id == "test_pet_123-battery-charging"
    assert sensor._attr_name == "Fido Collar Battery Charging"
    assert sensor._attr_device_class == BinarySensorDeviceClass.BATTERY_CHARGING
    assert sensor.is_on is True
    assert sensor.icon == "mdi:power-plug"

    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_pet_123")}
    assert device_info["name"] == "Fido"
    assert "Labrador" in device_info["model"]
    assert device_info["sw_version"] == "1.2.3"


async def test_battery_charging_sensor_off(
    hass: HomeAssistant, mock_coordinator_binary, mock_pet_charging
) -> None:
    """Test battery charging sensor when not charging."""
    mock_pet_charging.device.isCharging = False

    sensor = TryFiBatteryChargingBinarySensor(
        mock_coordinator_binary, mock_pet_charging
    )

    assert sensor.is_on is False
    assert sensor.icon == "mdi:power-plug-off"


async def test_battery_charging_sensor_no_device(
    hass: HomeAssistant, mock_coordinator_binary, mock_pet_charging
) -> None:
    """Test battery charging sensor with no device data."""
    mock_pet_charging.device = None

    sensor = TryFiBatteryChargingBinarySensor(
        mock_coordinator_binary, mock_pet_charging
    )

    assert sensor.is_on is None
    assert sensor.icon == "mdi:power-plug-off"  # Default to off icon


async def test_battery_charging_sensor_no_pet(
    hass: HomeAssistant, mock_coordinator_binary
) -> None:
    """Test battery charging sensor when pet data is not available."""
    mock_coordinator_binary.data.getPet.return_value = None

    mock_pet = Mock()
    mock_pet.petId = "test_pet"
    mock_pet.name = "Test"

    sensor = TryFiBatteryChargingBinarySensor(mock_coordinator_binary, mock_pet)

    assert sensor.is_on is None
    assert sensor.device_info == {}


async def test_battery_charging_sensor_missing_charging_attr(
    hass: HomeAssistant, mock_coordinator_binary, mock_pet_charging
) -> None:
    """Test battery charging sensor with missing isCharging attribute."""
    # Create device without isCharging attribute
    mock_pet_charging.device = Mock(spec=["buildId"])
    mock_pet_charging.device.buildId = "1.2.3"

    sensor = TryFiBatteryChargingBinarySensor(
        mock_coordinator_binary, mock_pet_charging
    )

    # Should default to False when attribute is missing
    assert sensor.is_on is False
