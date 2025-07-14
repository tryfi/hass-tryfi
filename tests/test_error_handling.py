"""Test error handling in TryFi integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.tryfi.coordinator import TryFiDataUpdateCoordinator
from custom_components.tryfi.light import TryFiPetLight
from custom_components.tryfi.select import TryFiLostModeSelect
from custom_components.tryfi.sensor import PetStatsSensor, TryFiBatterySensor


async def test_coordinator_update_failure(hass: HomeAssistant) -> None:
    """Test coordinator handling update failures."""
    mock_tryfi = Mock()
    mock_tryfi.update = Mock(side_effect=Exception("API Error"))

    coordinator = TryFiDataUpdateCoordinator(hass, mock_tryfi, 30)

    # Should raise UpdateFailed
    with pytest.raises(Exception) as exc_info:
        await coordinator._async_update_data()

    assert "API Error" in str(exc_info.value)


async def test_sensor_missing_stats(hass: HomeAssistant) -> None:
    """Test sensor with missing statistics data."""
    coordinator = Mock()
    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test"
    pet.dailySteps = None
    # No stats attribute

    coordinator.data.getPet.return_value = pet

    sensor = PetStatsSensor(coordinator, pet, "STEPS", "DAILY")
    assert sensor.native_value is None

    # With stats but missing key
    pet.stats = {"DAILY": {}}
    assert sensor.native_value is None

    # With stats but wrong structure
    pet.stats = "invalid"
    assert sensor.native_value is None


async def test_light_invalid_color(hass: HomeAssistant) -> None:
    """Test light with invalid color data."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.async_request_refresh = AsyncMock()

    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test"
    pet.device = Mock()
    pet.device.ledOn = True
    pet.device.ledColorHex = "INVALID"
    pet.device.availableLedColors = []

    coordinator.data.getPet.return_value = pet

    light = TryFiPetLight(coordinator, pet)

    # Should handle invalid color gracefully
    assert light.rgb_color is None


async def test_select_entity_errors(hass: HomeAssistant) -> None:
    """Test select entity error handling."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.session = Mock()
    coordinator.async_request_refresh = AsyncMock()

    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test"
    pet.setLostDogMode = Mock(side_effect=Exception("API Error"))

    coordinator.data.getPet.return_value = pet

    select = TryFiLostModeSelect(coordinator, pet)
    select.hass = hass

    # Should handle error gracefully
    await select.async_select_option("Lost")

    # Should have called setLostDogMode but not crashed
    pet.setLostDogMode.assert_called_once()


async def test_battery_sensor_type_errors(hass: HomeAssistant) -> None:
    """Test battery sensor with type errors."""
    coordinator = Mock()
    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test"
    pet.device = Mock()
    pet.device.batteryPercent = "not_a_number"  # Invalid type

    coordinator.data.getPet.return_value = pet

    sensor = TryFiBatterySensor(coordinator, pet)

    # Should return the string without crashing
    assert sensor.native_value == "not_a_number"


async def test_device_tracker_coordinate_errors(hass: HomeAssistant) -> None:
    """Test device tracker with coordinate parsing errors."""
    from custom_components.tryfi.device_tracker import TryFiPetTracker

    coordinator = Mock()
    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test"
    pet.currLatitude = None
    pet.currLongitude = None

    coordinator.data.getPet.return_value = pet

    tracker = TryFiPetTracker(coordinator, pet)

    # Should handle conversion error
    assert tracker.latitude is None
    assert tracker.longitude is None


async def test_entity_availability(hass: HomeAssistant) -> None:
    """Test entity availability when coordinator has no data."""
    coordinator = Mock()
    coordinator.data = None

    pet = Mock()
    pet.petId = "test_pet"
    pet.name = "Test"

    # Test various entities with no coordinator data
    with patch.object(coordinator, "data", None):
        sensor = TryFiBatterySensor(coordinator, pet)
        assert sensor.native_value is None


async def test_config_flow_validation_errors(hass: HomeAssistant) -> None:
    """Test config flow with various validation errors."""
    from custom_components.tryfi.config_flow import validate_input

    # Test with invalid polling rate (handled by schema validation)
    # Test with connection timeout
    with patch(
        "custom_components.tryfi.pytryfi.PyTryFi",
        side_effect=TimeoutError("Connection timeout"),
    ):
        with pytest.raises(Exception):
            await validate_input(
                hass,
                {
                    "username": "test@example.com",
                    "password": "test-password",
                    "polling": 30,
                },
            )
