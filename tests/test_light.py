"""Test TryFi light platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from homeassistant.components.light import (
    ATTR_RGB_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.tryfi.const import DOMAIN
from custom_components.tryfi.light import (
    calculate_distance,
    find_closest_color_code,
    hex_to_rgb,
)

from tests.common import MockConfigEntry


def test_hex_to_rgb():
    """Test hex to RGB conversion."""
    assert hex_to_rgb("#FF0000") == (255, 0, 0)
    assert hex_to_rgb("00FF00") == (0, 255, 0)
    assert hex_to_rgb("#0000FF") == (0, 0, 255)
    assert hex_to_rgb("FFFFFF") == (255, 255, 255)


def test_calculate_distance():
    """Test color distance calculation."""
    assert calculate_distance((0, 0, 0), (0, 0, 0)) == 0
    assert calculate_distance((255, 0, 0), (255, 0, 0)) == 0
    assert calculate_distance((0, 0, 0), (255, 255, 255)) == pytest.approx(441.67, 0.01)
    assert calculate_distance((255, 0, 0), (0, 255, 0)) == pytest.approx(360.62, 0.01)


def test_find_closest_color_code():
    """Test finding closest color code."""
    color_map = {
        1: (255, 0, 0),    # Red
        2: (0, 255, 0),    # Green
        3: (0, 0, 255),    # Blue
        8: (255, 255, 255), # White
    }
    
    # Exact matches
    assert find_closest_color_code((255, 0, 0), color_map) == 1
    assert find_closest_color_code((0, 255, 0), color_map) == 2
    assert find_closest_color_code((0, 0, 255), color_map) == 3
    
    # Close to red
    assert find_closest_color_code((200, 50, 50), color_map) == 1
    
    # Close to white
    assert find_closest_color_code((200, 200, 200), color_map) == 8


@pytest.fixture
def mock_pet_with_light():
    """Create a mock pet with light capabilities."""
    pet = Mock()
    pet.petId = "test_pet_123"
    pet.name = "Fido"
    pet.device = Mock()
    pet.device.ledOn = True
    pet.device.ledColorHex = "#FF0000"
    pet.device.availableLedColors = [
        Mock(ledColorCode=1, hexCode="#FF0000"),
        Mock(ledColorCode=2, hexCode="#00FF00"),
        Mock(ledColorCode=3, hexCode="#0000FF"),
        Mock(ledColorCode=8, hexCode="#FFFFFF"),
    ]
    pet.turnOnOffLed = Mock()
    pet.setLedColorCode = Mock()
    return pet


@pytest.fixture
def mock_coordinator_with_light(mock_pet_with_light):
    """Create a mock coordinator with light data."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.pets = [mock_pet_with_light]
    coordinator.data.getPet = Mock(return_value=mock_pet_with_light)
    coordinator.data.session = Mock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def test_light_entity_properties(
    hass: HomeAssistant,
    mock_coordinator_with_light,
    mock_pet_with_light
) -> None:
    """Test TryFi light entity properties."""
    from custom_components.tryfi.light import TryFiPetLight
    
    light = TryFiPetLight(mock_coordinator_with_light, mock_pet_with_light)
    
    assert light.unique_id == "test_pet_123-light"
    assert light.name == "Fido Collar Light"
    assert light.is_on is True
    assert light.rgb_color == (255, 0, 0)
    assert light.device_info["identifiers"] == {(DOMAIN, "test_pet_123")}
    
    # Test with light off
    mock_pet_with_light.device.ledOn = False
    assert light.is_on is False
    
    # Test with invalid hex color
    mock_pet_with_light.device.ledColorHex = "invalid"
    assert light.rgb_color is None


async def test_light_turn_on(
    hass: HomeAssistant,
    mock_coordinator_with_light,
    mock_pet_with_light
) -> None:
    """Test turning on the light."""
    from custom_components.tryfi.light import TryFiPetLight
    
    light = TryFiPetLight(mock_coordinator_with_light, mock_pet_with_light)
    light.hass = hass
    
    # Turn on without color
    await light.async_turn_on()
    
    mock_pet_with_light.turnOnOffLed.assert_called_once_with(
        mock_coordinator_with_light.data.session,
        True
    )
    mock_coordinator_with_light.async_request_refresh.assert_called_once()
    
    # Reset mocks
    mock_pet_with_light.turnOnOffLed.reset_mock()
    mock_coordinator_with_light.async_request_refresh.reset_mock()
    
    # Turn on with color
    await light.async_turn_on(**{ATTR_RGB_COLOR: (0, 255, 0)})
    
    mock_pet_with_light.turnOnOffLed.assert_called_once_with(
        mock_coordinator_with_light.data.session,
        True
    )
    mock_pet_with_light.setLedColorCode.assert_called_once_with(
        mock_coordinator_with_light.data.session,
        2  # Green color code
    )
    assert mock_coordinator_with_light.async_request_refresh.call_count == 1


async def test_light_turn_off(
    hass: HomeAssistant,
    mock_coordinator_with_light,
    mock_pet_with_light
) -> None:
    """Test turning off the light."""
    from custom_components.tryfi.light import TryFiPetLight
    
    light = TryFiPetLight(mock_coordinator_with_light, mock_pet_with_light)
    light.hass = hass
    
    await light.async_turn_off()
    
    mock_pet_with_light.turnOnOffLed.assert_called_once_with(
        mock_coordinator_with_light.data.session,
        False
    )
    mock_coordinator_with_light.async_request_refresh.assert_called_once()


async def test_light_no_pet_data(
    hass: HomeAssistant,
    mock_coordinator_with_light
) -> None:
    """Test light when pet data is not available."""
    from custom_components.tryfi.light import TryFiPetLight
    
    mock_coordinator_with_light.data.getPet.return_value = None
    
    mock_pet = Mock()
    mock_pet.petId = "test_pet"
    mock_pet.name = "Test"
    mock_pet.device = Mock()
    
    light = TryFiPetLight(mock_coordinator_with_light, mock_pet)
    light.hass = hass
    
    assert light.is_on is None
    assert light.rgb_color is None
    
    # Try to turn on/off - should log error and return
    await light.async_turn_on()
    await light.async_turn_off()
    
    # Should not crash, just return early
    mock_coordinator_with_light.async_request_refresh.assert_not_called()