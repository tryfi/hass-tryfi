"""Test TryFi sensor platform."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from homeassistant.const import (
    UnitOfLength,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant

from custom_components.tryfi.const import DOMAIN
from custom_components.tryfi.sensor import (
    PetGenericSensor,
    PetStatsSensor,
    TryFiBatterySensor,
    TryFiBaseSensor,
)


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


async def test_battery_sensor(
    hass: HomeAssistant, mock_coordinator, mock_pet_with_stats
) -> None:
    """Test TryFi battery sensor."""
    mock_coordinator.data.getPet.return_value = mock_pet_with_stats

    sensor = TryFiBatterySensor(mock_coordinator, mock_pet_with_stats)

    assert sensor.unique_id == "test_pet_123-battery"
    assert sensor.name == "Fido Collar Battery Level"
    assert sensor.native_value == 75
    assert sensor.device_info["identifiers"] == {(DOMAIN, "test_pet_123")}
    assert sensor.icon == "mdi:battery-80"

    # Test charging icon
    mock_pet_with_stats.device.isCharging = True
    assert sensor.icon == "mdi:battery-charging"

    # Test low battery
    mock_pet_with_stats.device.batteryPercent = 5
    mock_pet_with_stats.device.isCharging = False
    assert sensor.native_value == 5
    assert sensor.icon == "mdi:battery-alert"


async def test_stats_sensor(
    hass: HomeAssistant, mock_coordinator, mock_pet_with_stats
) -> None:
    """Test TryFi statistics sensor."""
    mock_coordinator.data.getPet.return_value = mock_pet_with_stats

    # Test daily steps sensor
    sensor = PetStatsSensor(mock_coordinator, mock_pet_with_stats, "STEPS", "DAILY")

    assert sensor.unique_id == "test_pet_123-daily-steps"
    assert sensor.name == "Fido Daily Steps"
    assert sensor.native_value == 5000
    assert sensor.icon == "mdi:paw"

    # Test weekly distance sensor
    sensor = PetStatsSensor(mock_coordinator, mock_pet_with_stats, "DISTANCE", "WEEKLY")

    assert sensor.unique_id == "test_pet_123-weekly-distance"
    assert sensor.name == "Fido Weekly Distance"
    assert sensor.native_value == 17.5
    assert sensor.native_unit_of_measurement == UnitOfLength.KILOMETERS

    # Test monthly sleep sensor
    sensor = PetStatsSensor(mock_coordinator, mock_pet_with_stats, "SLEEP", "MONTHLY")

    assert sensor.unique_id == "test_pet_123-monthly-sleep"
    assert sensor.name == "Fido Monthly Sleep"
    assert sensor.native_value == 14400
    assert sensor.native_unit_of_measurement == UnitOfTime.MINUTES


async def test_generic_sensor(
    hass: HomeAssistant, mock_coordinator, mock_pet_with_stats
) -> None:
    """Test TryFi generic sensor."""
    mock_coordinator.data.getPet.return_value = mock_pet_with_stats

    # Test activity type sensor
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "Activity Type")

    assert sensor.unique_id == "test_pet_123-activity-type"
    assert sensor.name == "Fido Activity Type"
    assert sensor.native_value == "REST"
    assert sensor.icon == "mdi:run"

    # Test current place sensor
    sensor = PetGenericSensor(
        mock_coordinator, mock_pet_with_stats, "Current Place Name"
    )

    assert sensor.unique_id == "test_pet_123-current-place-name"
    assert sensor.name == "Fido Current Place Name"
    assert sensor.native_value == "Home"
    assert sensor.icon == "mdi:map-marker"

    # Test connection sensor
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "Connected To")

    assert sensor.unique_id == "test_pet_123-connected-to"
    assert sensor.name == "Fido Connected To"
    assert sensor.native_value == "Cellular"
    assert sensor.icon == "mdi:wifi"


async def test_base_sensor(hass: HomeAssistant, mock_coordinator) -> None:
    """Test TryFi base station sensor."""
    mock_base = Mock()
    mock_base.baseId = "base_123"
    mock_base.name = "Living Room Base"
    mock_base.online = True

    mock_coordinator.data.getBase.return_value = mock_base

    sensor = TryFiBaseSensor(mock_coordinator, mock_base)

    assert sensor.unique_id == "base_123"
    assert sensor.name == "Living Room Base"
    assert sensor.native_value == "Online"
    assert sensor.icon == "mdi:home-circle"
    assert sensor.device_info["identifiers"] == {(DOMAIN, "base_123")}

    # Test offline base
    mock_base.online = False
    assert sensor.native_value == "Offline"


async def test_sensor_no_data(hass: HomeAssistant, mock_coordinator) -> None:
    """Test sensors when no data is available."""
    mock_coordinator.data.getPet.return_value = None

    mock_pet = Mock()
    mock_pet.petId = "test_pet"
    mock_pet.name = "Test"

    # Test battery sensor with no data
    sensor = TryFiBatterySensor(mock_coordinator, mock_pet)
    assert sensor.native_value is None

    # Test stats sensor with no data
    sensor = PetStatsSensor(mock_coordinator, mock_pet, "STEPS", "DAILY")
    assert sensor.native_value is None

    # Test generic sensor with no data
    sensor = PetGenericSensor(mock_coordinator, mock_pet, "Activity Type")
    assert sensor.native_value is None
