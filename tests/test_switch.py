"""Test TryFi switch platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.tryfi.const import DOMAIN, MANUFACTURER, MODEL
from custom_components.tryfi.switch import TryFiLostModeSwitch, async_setup_entry


@pytest.fixture
def mock_pet_switch():
    """Create a mock pet with switch capabilities."""
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
def mock_coordinator_switch(mock_pet_switch):
    """Create a mock coordinator for switch tests."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.pets = [mock_pet_switch]
    coordinator.data.getPet = Mock(return_value=mock_pet_switch)
    coordinator.data.session = Mock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def test_async_setup_entry(
    hass: HomeAssistant, mock_coordinator_switch, mock_pet_switch
) -> None:
    """Test setting up switch entities from config entry."""
    pet_without_device = Mock()
    pet_without_device.petId = "pet_no_device"
    pet_without_device.device = None

    mock_coordinator_switch.data.pets = [mock_pet_switch, pet_without_device]

    config_entry = Mock()
    config_entry.entry_id = "test_entry"

    hass.data = {DOMAIN: {"test_entry": mock_coordinator_switch}}

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    assert async_add_entities.called
    added_entities = async_add_entities.call_args[0][0]
    assert len(added_entities) == 1
    assert isinstance(added_entities[0], TryFiLostModeSwitch)
    assert added_entities[0]._pet_id == "test_pet_123"


async def test_lost_mode_switch_properties(
    hass: HomeAssistant, mock_coordinator_switch, mock_pet_switch
) -> None:
    """Test lost mode switch entity properties."""
    switch = TryFiLostModeSwitch(mock_coordinator_switch, mock_pet_switch)

    assert switch._attr_unique_id == "test_pet_123-lost-mode-switch"
    assert switch._attr_name == "Fido Lost Mode Switch"
    assert switch._attr_icon == "mdi:map-search"
    assert switch.is_on is False
    assert switch.available is True

    device_info = switch.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_pet_123")}
    assert device_info["name"] == "Fido"
    assert "Labrador" in device_info["model"]
    assert device_info["sw_version"] == "1.2.3"

    # Test when pet is lost
    mock_pet_switch.isLost = True
    assert switch.is_on is True


async def test_lost_mode_switch_no_pet(
    hass: HomeAssistant, mock_coordinator_switch, mock_pet_switch
) -> None:
    """Test lost mode switch when pet data is not available."""
    mock_coordinator_switch.data.getPet.return_value = None

    switch = TryFiLostModeSwitch(mock_coordinator_switch, mock_pet_switch)
    switch.hass = hass

    assert switch.is_on is None
    assert switch.available is False
    assert switch.device_info == {}

    # Test turn on / off with no pet
    await switch.async_turn_on()
    mock_pet_switch.setLostDogMode.assert_not_called()
    mock_coordinator_switch.async_request_refresh.assert_not_called()

    await switch.async_turn_off()
    mock_pet_switch.setLostDogMode.assert_not_called()
    mock_coordinator_switch.async_request_refresh.assert_not_called()


async def test_lost_mode_switch_turn_on(
    hass: HomeAssistant, mock_coordinator_switch, mock_pet_switch
) -> None:
    """Test turning on lost mode switch."""
    switch = TryFiLostModeSwitch(mock_coordinator_switch, mock_pet_switch)
    switch.hass = hass

    await switch.async_turn_on()

    mock_pet_switch.setLostDogMode.assert_called_once_with(
        mock_coordinator_switch.data.session, True
    )
    mock_coordinator_switch.async_request_refresh.assert_called_once()


async def test_lost_mode_switch_turn_off(
    hass: HomeAssistant, mock_coordinator_switch, mock_pet_switch
) -> None:
    """Test turning off lost mode switch."""
    switch = TryFiLostModeSwitch(mock_coordinator_switch, mock_pet_switch)
    switch.hass = hass

    await switch.async_turn_off()

    mock_pet_switch.setLostDogMode.assert_called_once_with(
        mock_coordinator_switch.data.session, False
    )
    mock_coordinator_switch.async_request_refresh.assert_called_once()
