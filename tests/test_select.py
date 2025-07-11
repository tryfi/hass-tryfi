"""Test TryFi select platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.tryfi.const import DOMAIN
from custom_components.tryfi.select import LOST_MODE_OPTIONS, TryFiLostModeSelect



@pytest.fixture
def mock_pet_lost_mode():
    """Create a mock pet with lost mode data."""
    pet = Mock()
    pet.petId = "test_pet_123"
    pet.name = "Fido"
    pet.breed = "Labrador"
    pet.isLost = False
    pet.device = Mock()
    pet.device.buildId = "1.2.3"
    pet.setLostDogMode = Mock()
    return pet


@pytest.fixture
def mock_coordinator_select(mock_pet_lost_mode):
    """Create a mock coordinator for select tests."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.getPet = Mock(return_value=mock_pet_lost_mode)
    coordinator.data.session = Mock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def test_lost_mode_select_safe(
    hass: HomeAssistant,
    mock_coordinator_select,
    mock_pet_lost_mode
) -> None:
    """Test lost mode select when pet is safe."""
    select = TryFiLostModeSelect(mock_coordinator_select, mock_pet_lost_mode)
    
    assert select._attr_unique_id == "test_pet_123-lost"
    assert select._attr_name == "Fido Lost Mode"
    assert select._attr_options == LOST_MODE_OPTIONS
    assert select._attr_icon == "mdi:map-search"
    assert select.current_option == "Safe"
    assert select.available is True
    
    device_info = select.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_pet_123")}
    assert device_info["name"] == "Fido"
    assert "Labrador" in device_info["model"]
    assert device_info["sw_version"] == "1.2.3"


async def test_lost_mode_select_lost(
    hass: HomeAssistant,
    mock_coordinator_select,
    mock_pet_lost_mode
) -> None:
    """Test lost mode select when pet is lost."""
    mock_pet_lost_mode.isLost = True
    
    select = TryFiLostModeSelect(mock_coordinator_select, mock_pet_lost_mode)
    
    assert select.current_option == "Lost"


async def test_lost_mode_select_change_to_lost(
    hass: HomeAssistant,
    mock_coordinator_select,
    mock_pet_lost_mode
) -> None:
    """Test changing lost mode to Lost."""
    select = TryFiLostModeSelect(mock_coordinator_select, mock_pet_lost_mode)
    select.hass = hass
    
    await select.async_select_option("Lost")
    
    mock_pet_lost_mode.setLostDogMode.assert_called_once_with(
        mock_coordinator_select.data.session,
        True
    )
    mock_coordinator_select.async_request_refresh.assert_called_once()


async def test_lost_mode_select_change_to_safe(
    hass: HomeAssistant,
    mock_coordinator_select,
    mock_pet_lost_mode
) -> None:
    """Test changing lost mode to Safe."""
    mock_pet_lost_mode.isLost = True
    
    select = TryFiLostModeSelect(mock_coordinator_select, mock_pet_lost_mode)
    select.hass = hass
    
    await select.async_select_option("Safe")
    
    mock_pet_lost_mode.setLostDogMode.assert_called_once_with(
        mock_coordinator_select.data.session,
        False
    )
    mock_coordinator_select.async_request_refresh.assert_called_once()


async def test_lost_mode_select_invalid_option(
    hass: HomeAssistant,
    mock_coordinator_select,
    mock_pet_lost_mode
) -> None:
    """Test selecting an invalid option."""
    select = TryFiLostModeSelect(mock_coordinator_select, mock_pet_lost_mode)
    select.hass = hass
    
    await select.async_select_option("Invalid")
    
    # Should not call setLostDogMode
    mock_pet_lost_mode.setLostDogMode.assert_not_called()
    mock_coordinator_select.async_request_refresh.assert_not_called()


async def test_lost_mode_select_no_pet(
    hass: HomeAssistant,
    mock_coordinator_select
) -> None:
    """Test lost mode select when pet data is not available."""
    mock_coordinator_select.data.getPet.return_value = None
    
    mock_pet = Mock()
    mock_pet.petId = "test_pet"
    mock_pet.name = "Test"
    
    select = TryFiLostModeSelect(mock_coordinator_select, mock_pet)
    select.hass = hass
    
    assert select.current_option is None
    assert select.available is False
    assert select.device_info == {}
    
    # Try to select option - should log error and return
    await select.async_select_option("Lost")
    
    mock_coordinator_select.async_request_refresh.assert_not_called()


async def test_lost_mode_select_missing_lost_attr(
    hass: HomeAssistant,
    mock_coordinator_select,
    mock_pet_lost_mode
) -> None:
    """Test lost mode select with missing isLost attribute."""
    # Remove isLost attribute
    delattr(mock_pet_lost_mode, "isLost")
    
    select = TryFiLostModeSelect(mock_coordinator_select, mock_pet_lost_mode)
    
    # Should default to Safe when attribute is missing
    assert select.current_option == "Safe"