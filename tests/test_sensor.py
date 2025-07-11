"""Test TryFi sensor platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.components.sensor import ATTR_STATE_CLASS
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_UNKNOWN,
    UnitOfLength,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.tryfi.const import DOMAIN
from custom_components.tryfi.sensor import (
    PetGenericSensor,
    PetStatsSensor,
    TryFiBatterySensor,
    TryFiBaseSensor,
)

from tests.common import MockConfigEntry


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
    pet.currentPlaceName = "Home"
    pet.currentPlaceAddress = "123 Main St"
    pet.device = Mock()
    pet.device.batteryPercent = 75
    pet.device.isCharging = False
    pet.device.connectionState = "CONNECTED"
    pet.stats = {
        "DAILY": {"STEPS": 5000, "DISTANCE": 2.5, "SLEEP": 480, "NAP": 120},
        "WEEKLY": {"STEPS": 35000, "DISTANCE": 17.5, "SLEEP": 3360, "NAP": 840},
        "MONTHLY": {"STEPS": 150000, "DISTANCE": 75, "SLEEP": 14400, "NAP": 3600},
    }
    return pet


async def test_battery_sensor(
    hass: HomeAssistant, mock_coordinator, mock_pet_with_stats
) -> None:
    """Test TryFi battery sensor."""
    mock_coordinator.data.getPet.return_value = mock_pet_with_stats
    
    sensor = TryFiBatterySensor(mock_coordinator, mock_pet_with_stats)
    
    assert sensor.unique_id == "test_pet_123_battery_level"
    assert sensor.name == "Fido Collar Battery Level"
    assert sensor.native_value == 75
    assert sensor.device_info["identifiers"] == {(DOMAIN, "test_pet_123")}
    assert sensor.icon == "mdi:battery-70"
    
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
    
    assert sensor.unique_id == "test_pet_123_daily_steps"
    assert sensor.name == "Fido Daily Steps"
    assert sensor.native_value == 5000
    assert sensor.icon == "mdi:paw"
    
    # Test weekly distance sensor
    sensor = PetStatsSensor(mock_coordinator, mock_pet_with_stats, "DISTANCE", "WEEKLY")
    
    assert sensor.unique_id == "test_pet_123_weekly_distance"
    assert sensor.name == "Fido Weekly Distance"
    assert sensor.native_value == 17.5
    assert sensor.native_unit_of_measurement == UnitOfLength.KILOMETERS
    
    # Test monthly sleep sensor
    sensor = PetStatsSensor(mock_coordinator, mock_pet_with_stats, "SLEEP", "MONTHLY")
    
    assert sensor.unique_id == "test_pet_123_monthly_sleep"
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
    
    assert sensor.unique_id == "test_pet_123_activity_type"
    assert sensor.name == "Fido Activity Type"
    assert sensor.native_value == "REST"
    assert sensor.icon == "mdi:run"
    
    # Test current place sensor
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "Current Place Name")
    
    assert sensor.unique_id == "test_pet_123_current_place_name"
    assert sensor.name == "Fido Current Place Name"
    assert sensor.native_value == "Home"
    assert sensor.icon == "mdi:map-marker"
    
    # Test connection sensor
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "Connected To")
    
    assert sensor.unique_id == "test_pet_123_connected_to"
    assert sensor.name == "Fido Connected To"
    assert sensor.native_value == "CONNECTED"
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
    assert sensor.device_info["identifiers"] == {(DOMAIN, "base_base_123")}
    
    # Test offline base
    mock_base.online = False
    assert sensor.native_value == "Offline"


async def test_sensor_no_data(
    hass: HomeAssistant, mock_coordinator
) -> None:
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