"""Test TryFi device tracker platform."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from homeassistant.components.device_tracker import SourceType
from homeassistant.core import HomeAssistant

from custom_components.tryfi.const import DOMAIN, MANUFACTURER, MODEL
from custom_components.tryfi.device_tracker import (
    TryFiBaseTracker,
    TryFiPetTracker,
    TryFiWifiNetworkTracker,
    async_setup_entry,
)


@pytest.fixture
def mock_pet_location():
    """Create a mock pet with location data."""
    pet = Mock()
    pet.petId = "test_pet_123"
    pet.name = "Fido"
    pet.photoLink = "https://example.com/photo.jpg"
    pet.currLatitude = 40.7128
    pet.currLongitude = -74.0060
    pet.positionAccuracy = 15.0
    pet.breed = "Labrador"
    pet.device = Mock()
    pet.device.batteryPercent = 85
    pet.device.buildId = "1.2.3"
    return pet


@pytest.fixture
def mock_base_location():
    """Create a mock base with location data."""
    base = Mock()
    base.baseId = "base_123"
    base.name = "Home Base"
    base.latitude = 40.7128
    base.longitude = -74.0060
    return base


@pytest.fixture
def mock_wifi_network():
    """Create a mock wifi network."""
    network = Mock()
    network.ssid = "HomeWiFi"
    network.latitude = 40.7128
    network.longitude = -74.0060
    return network


@pytest.fixture
def mock_coordinator_tracker(mock_pet_location, mock_base_location, mock_wifi_network):
    """Create a mock coordinator for tracker tests."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.pets = [mock_pet_location]
    coordinator.data.bases = [mock_base_location]
    coordinator.data.wifiNetworks = [mock_wifi_network]
    coordinator.data.getPet = Mock(return_value=mock_pet_location)
    coordinator.data.getBase = Mock(return_value=mock_base_location)
    coordinator.data.getWifiNetwork = Mock(return_value=mock_wifi_network)
    coordinator.async_add_listener = Mock(return_value=Mock())
    return coordinator


async def test_async_setup_entry(
    hass: HomeAssistant, mock_coordinator_tracker
) -> None:
    """Test setup entry for device trackers."""
    config_entry = Mock()
    config_entry.entry_id = "test_entry"
    config_entry.async_on_unload = Mock()

    hass.data = {DOMAIN: {"test_entry": mock_coordinator_tracker}}

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    assert async_add_entities.called
    added_entities = async_add_entities.call_args[0][0]
    # Expect: PetTracker, BaseTracker, WifiNetworkTracker
    assert len(added_entities) == 3
    assert any(isinstance(e, TryFiPetTracker) for e in added_entities)
    assert any(isinstance(e, TryFiBaseTracker) for e in added_entities)
    assert any(isinstance(e, TryFiWifiNetworkTracker) for e in added_entities)

    # Test listener callback for new wifi networks
    assert mock_coordinator_tracker.async_add_listener.called
    listener_cb = mock_coordinator_tracker.async_add_listener.call_args[0][0]

    # Add a new wifi network
    new_wifi = Mock()
    new_wifi.ssid = "GuestWiFi"
    mock_coordinator_tracker.data.wifiNetworks.append(new_wifi)

    async_add_entities.reset_mock()
    listener_cb()

    assert async_add_entities.called
    new_added = async_add_entities.call_args[0][0]
    assert len(new_added) == 1
    assert isinstance(new_added[0], TryFiWifiNetworkTracker)
    assert new_added[0]._ssid == "GuestWiFi"


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
    assert tracker.location_accuracy == 15.0
    assert tracker.source_type == SourceType.GPS

    device_info = tracker.device_info
    assert device_info["identifiers"] == {(DOMAIN, "test_pet_123")}
    assert device_info["name"] == "Fido"
    assert "Labrador" in device_info["model"]
    assert device_info["sw_version"] == "1.2.3"


async def test_tracker_location_accuracy_none_and_no_breed(
    hass: HomeAssistant, mock_coordinator_tracker, mock_pet_location
) -> None:
    """Test tracker location_accuracy fallback to 0 and model fallback when no breed."""
    mock_pet_location.positionAccuracy = None
    delattr(mock_pet_location, "breed")

    tracker = TryFiPetTracker(mock_coordinator_tracker, mock_pet_location)

    assert tracker.location_accuracy == 0
    assert tracker.device_info["model"] == MODEL


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
    pet = Mock(
        spec=[
            "petId",
            "name",
            "breed",
            "device",
            "positionAccuracy",
            "photoLink",
            "currLatitude",
            "currLongitude",
        ]
    )
    pet.petId = "test_pet_123"
    pet.name = "Fido"
    pet.positionAccuracy = None
    pet.photoLink = None
    pet.currLatitude = None
    pet.currLongitude = None
    pet.breed = "Breed"
    pet.device = Mock(spec=[])

    mock_coordinator_tracker.data.getPet.return_value = pet

    tracker = TryFiPetTracker(mock_coordinator_tracker, pet)

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
    mock_pet_location.device = None

    tracker = TryFiPetTracker(mock_coordinator_tracker, mock_pet_location)

    assert tracker.battery_level is None
    assert "sw_version" not in tracker.device_info

    mock_pet_location.device = Mock(spec=[])
    assert tracker.battery_level is None


async def test_base_tracker(
    hass: HomeAssistant, mock_coordinator_tracker, mock_base_location
) -> None:
    """Test TryFi base tracker."""
    tracker = TryFiBaseTracker(mock_coordinator_tracker, mock_base_location)

    assert tracker._attr_unique_id == "base_123-tracker"
    assert tracker._attr_name == "Home Base Tracker"
    assert tracker._attr_icon == "mdi:home-map-marker"
    assert tracker.latitude == 40.7128
    assert tracker.longitude == -74.0060
    assert tracker.source_type == SourceType.GPS

    device_info = tracker.device_info
    assert device_info["identifiers"] == {(DOMAIN, "base_123")}
    assert device_info["name"] == "Home Base"
    assert device_info["manufacturer"] == MANUFACTURER
    assert device_info["model"] == "TryFi Base Station"

    # Test missing latitude/longitude
    mock_base_location.latitude = None
    mock_base_location.longitude = None
    assert tracker.latitude is None
    assert tracker.longitude is None

    # Test base missing from coordinator
    mock_coordinator_tracker.data.getBase.return_value = None
    assert tracker.base is None
    assert tracker.latitude is None
    assert tracker.longitude is None
    assert tracker.device_info == {}


async def test_wifi_network_tracker(
    hass: HomeAssistant, mock_coordinator_tracker, mock_wifi_network
) -> None:
    """Test TryFi WiFi network tracker."""
    tracker = TryFiWifiNetworkTracker(mock_coordinator_tracker, mock_wifi_network)

    assert tracker._attr_unique_id == "wifi-HomeWiFi-tracker"
    assert tracker._attr_icon == "mdi:wifi-marker"
    assert tracker.latitude == 40.7128
    assert tracker.longitude == -74.0060
    assert tracker.source_type == SourceType.GPS

    device_info = tracker.device_info
    assert device_info["identifiers"] == {(DOMAIN, "wifi-HomeWiFi")}
    assert device_info["name"] == "WiFi HomeWiFi"
    assert device_info["manufacturer"] == MANUFACTURER
    assert device_info["model"] == "WiFi Network"

    # Test missing latitude/longitude
    mock_wifi_network.latitude = None
    mock_wifi_network.longitude = None
    assert tracker.latitude is None
    assert tracker.longitude is None

    # Test network missing from coordinator
    mock_coordinator_tracker.data.getWifiNetwork.return_value = None
    assert tracker.network is None
    assert tracker.latitude is None
    assert tracker.longitude is None
    assert tracker.device_info == {}
