"""Integration tests for TryFi."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import responses

from custom_components.tryfi.const import DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry

from .pytryfi.utils import (
    GRAPHQL_BASE,
    GRAPHQL_PARTIAL_PET,
    mock_household_with_pets,
    mock_login_requests,
)


@pytest.fixture
def mock_tryfi_api():
    """Create a fully mocked TryFi API."""
    with patch("custom_components.tryfi.pytryfi.PyTryFi") as mock_pytryfi:
        # Create instance
        instance = Mock()
        mock_pytryfi.return_value = instance

        # Setup user
        instance.currentUser = Mock()
        instance.currentUser.userId = "user123"
        instance.currentUser.email = "test@example.com"

        # Setup session
        instance.session = Mock()

        # Setup pets
        pet1 = Mock()
        pet1.petId = "pet1"
        pet1.name = "Buddy"
        pet1.breed = "Golden Retriever"
        pet1.photoLink = "https://example.com/buddy.jpg"
        pet1.currLatitude = "40.7128"
        pet1.currLongitude = "-74.0060"
        pet1.activityType = "REST"
        pet1.currentPlaceName = "Home"
        pet1.currentPlaceAddress = "123 Main St"
        pet1.isLost = False

        # Pet device
        pet1.device = Mock()
        pet1.device.moduleId = "module1"
        pet1.device.batteryPercent = 85
        pet1.device.isCharging = False
        pet1.device.ledOn = True
        pet1.device.ledColorHex = "#FF0000"
        pet1.device.ledColorCode = 1
        pet1.device.connectionState = "CONNECTED"
        pet1.device.buildId = "1.2.3"
        pet1.device.availableLedColors = [
            Mock(ledColorCode=1, hexCode="#FF0000"),
            Mock(ledColorCode=2, hexCode="#00FF00"),
            Mock(ledColorCode=3, hexCode="#0000FF"),
        ]

        # Pet stats
        pet1.stats = {
            "DAILY": {"STEPS": 5000, "DISTANCE": 2.5, "SLEEP": 480, "NAP": 120},
            "WEEKLY": {"STEPS": 35000, "DISTANCE": 17.5, "SLEEP": 3360, "NAP": 840},
            "MONTHLY": {"STEPS": 150000, "DISTANCE": 75, "SLEEP": 14400, "NAP": 3600},
        }

        # Pet methods
        pet1.turnOnOffLed = Mock()
        pet1.setLedColorCode = Mock()
        pet1.setLostDogMode = Mock()

        instance.pets = [pet1]
        instance.getPet = Mock(return_value=pet1)

        # Setup bases
        base1 = Mock()
        base1.baseId = "base1"
        base1.name = "Living Room Base"
        base1.online = True

        instance.bases = [base1]
        instance.getBase = Mock(return_value=base1)

        # Setup update method
        instance.update = Mock()

        yield instance


@responses.activate
async def test_full_integration_flow(hass: HomeAssistant, mock_tryfi_api) -> None:
    """Test complete integration setup flow."""
    mock_login_requests()
    mock_household_with_pets(pets=[GRAPHQL_PARTIAL_PET], bases=[GRAPHQL_BASE])

    # Create config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test@example.com",
            "password": "test-password",
            "polling": 30,
        },
    )
    config_entry.add_to_hass(hass)

    # Setup integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check that integration loaded
    assert config_entry.state == ConfigEntryState.LOADED

    # Check coordinator was created
    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    assert coordinator is not None

    # Check entities were created
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    # Check device was created
    devices = device_registry.devices
    pet_device = None
    for device in devices.values():
        if device.identifiers == {(DOMAIN, "test-pet")}:
            pet_device = device
            break

    assert pet_device is not None
    assert pet_device.name == "Buddy"
    assert pet_device.manufacturer == "TryFi"
    assert pet_device.model == "Smart Dog Collar - Golden Retriever"
    assert pet_device.sw_version == "1.2.3"

    # Check entities exist
    entities = er.async_entries_for_device(entity_registry, pet_device.id)
    entity_ids = {entity.entity_id for entity in entities}

    # Should have all entity types
    assert "device_tracker.buddy_tracker" in entity_ids
    assert "sensor.buddy_collar_battery_level" in entity_ids
    assert "sensor.buddy_daily_steps" in entity_ids
    assert "sensor.buddy_activity_type" in entity_ids
    assert "binary_sensor.buddy_collar_battery_charging" in entity_ids
    assert "light.buddy_collar_light" in entity_ids
    assert "select.buddy_lost_mode" in entity_ids

    # Test base entity
    base_entities = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )
    base_entity_ids = {entity.entity_id for entity in base_entities}
    assert "sensor.living_room_base" in base_entity_ids


@responses.activate
async def test_integration_reload(hass: HomeAssistant, mock_tryfi_api) -> None:
    """Test reloading the integration."""
    mock_login_requests()
    mock_household_with_pets()

    # Setup
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test@example.com",
            "password": "test-password",
            "polling": 30,
        },
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED

    # Reload
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.LOADED

    # Unload
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state == ConfigEntryState.NOT_LOADED
    assert config_entry.entry_id not in hass.data[DOMAIN]
