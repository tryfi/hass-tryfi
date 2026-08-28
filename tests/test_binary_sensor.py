"""Test TryFi binary sensor platform."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from custom_components.tryfi.binary_sensor import (
    TryFiBaseHealthBinarySensor,
    TryFiBatteryChargingBinarySensor,
    TryFiFirmwareUpdateBinarySensor,
    TryFiWifiNetworkHiddenBinarySensor,
    async_setup_entry,
)
from custom_components.tryfi.const import DOMAIN, MANUFACTURER


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
def mock_base():
    """Create a mock base."""
    base = Mock()
    base.baseId = "base_123"
    base.name = "Living Room Base"
    base.online = True
    base.onlineQuality = "HEALTHY"
    return base


@pytest.fixture
def mock_wifi_network():
    """Create a mock wifi network."""
    network = Mock()
    network.ssid = "MyHomeWiFi"
    network.isHidden = False
    return network


@pytest.fixture
def mock_coordinator_binary(mock_pet_charging, mock_base, mock_wifi_network):
    """Create a mock coordinator for binary sensor tests."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.pets = [mock_pet_charging]
    coordinator.data.bases = [mock_base]
    coordinator.data.wifiNetworks = [mock_wifi_network]
    coordinator.data.getPet = Mock(return_value=mock_pet_charging)
    coordinator.data.getBase = Mock(return_value=mock_base)
    coordinator.data.getWifiNetwork = Mock(return_value=mock_wifi_network)
    coordinator.async_add_listener = Mock(return_value=Mock())
    return coordinator


async def test_async_setup_entry(
    hass: HomeAssistant, mock_coordinator_binary, mock_wifi_network
) -> None:
    """Test setting up binary sensors via async_setup_entry."""
    config_entry = Mock()
    config_entry.entry_id = "test_entry"
    config_entry.async_on_unload = Mock()

    hass.data = {DOMAIN: {"test_entry": mock_coordinator_binary}}

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    assert async_add_entities.called
    added_entities = async_add_entities.call_args[0][0]
    # Expect: BatteryCharging, BaseHealth, FirmwareUpdate, WifiNetworkHidden
    assert len(added_entities) == 4
    assert any(isinstance(e, TryFiBatteryChargingBinarySensor) for e in added_entities)
    assert any(isinstance(e, TryFiBaseHealthBinarySensor) for e in added_entities)
    assert any(isinstance(e, TryFiFirmwareUpdateBinarySensor) for e in added_entities)
    assert any(isinstance(e, TryFiWifiNetworkHiddenBinarySensor) for e in added_entities)

    # Test coordinator listener callback for new WiFi networks
    assert mock_coordinator_binary.async_add_listener.called
    listener_cb = mock_coordinator_binary.async_add_listener.call_args[0][0]

    # Add a new wifi network to coordinator data
    new_wifi = Mock()
    new_wifi.ssid = "NewWiFi"
    new_wifi.isHidden = True
    mock_coordinator_binary.data.wifiNetworks.append(new_wifi)

    async_add_entities.reset_mock()
    listener_cb()

    assert async_add_entities.called
    new_added = async_add_entities.call_args[0][0]
    assert len(new_added) == 1
    assert isinstance(new_added[0], TryFiWifiNetworkHiddenBinarySensor)
    assert new_added[0]._ssid == "NewWiFi"


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
    mock_pet_charging.device = Mock(spec=["buildId"])
    mock_pet_charging.device.buildId = "1.2.3"

    sensor = TryFiBatteryChargingBinarySensor(
        mock_coordinator_binary, mock_pet_charging
    )

    assert sensor.is_on is False


async def test_base_health_binary_sensor(
    hass: HomeAssistant, mock_coordinator_binary, mock_base
) -> None:
    """Test base health binary sensor."""
    sensor = TryFiBaseHealthBinarySensor(mock_coordinator_binary, mock_base)

    assert sensor._attr_unique_id == "base_123-health"
    assert sensor._attr_name == "Living Room Base Connection Health"
    assert sensor._attr_device_class == BinarySensorDeviceClass.CONNECTIVITY
    assert sensor.is_on is True
    assert sensor.icon == "mdi:wifi-check"

    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, "base_123")}
    assert device_info["name"] == "Living Room Base"

    # Test base online quality unhealthy
    mock_base.onlineQuality = "UNHEALTHY"
    assert sensor.is_on is False
    assert sensor.icon == "mdi:wifi-alert"

    # Test base offline
    mock_base.online = False
    assert sensor.is_on is False
    assert sensor.icon == "mdi:wifi-alert"

    # Test base online without onlineQuality attribute
    mock_base.online = True
    delattr(mock_base, "onlineQuality")
    assert sensor.is_on is True
    assert sensor.icon == "mdi:wifi-check"

    # Test base missing from coordinator
    mock_coordinator_binary.data.getBase.return_value = None
    assert sensor.is_on is None
    assert sensor.device_info == {}


async def test_firmware_update_binary_sensor(
    hass: HomeAssistant, mock_coordinator_binary, mock_pet_charging
) -> None:
    """Test firmware update binary sensor."""
    sensor = TryFiFirmwareUpdateBinarySensor(
        mock_coordinator_binary, mock_pet_charging
    )

    assert sensor._attr_unique_id == "test_pet_123-firmware-update"
    assert sensor._attr_name == "Fido Firmware Update Available"
    assert sensor._attr_device_class == BinarySensorDeviceClass.UPDATE
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC

    # Version 1.2.3 != 3.3.0 -> update available
    assert sensor.is_on is True
    assert sensor.icon == "mdi:update"

    attrs = sensor.extra_state_attributes
    assert attrs["current_version"] == "1.2.3"
    assert attrs["latest_version"] == "3.3.0"

    device_info = sensor.device_info
    assert device_info["sw_version"] == "1.2.3"

    # Latest version -> update not available
    mock_pet_charging.device.buildId = "3.3.0"
    assert sensor.is_on is False
    assert sensor.icon == "mdi:check-circle"

    # No device or buildId
    mock_pet_charging.device = None
    assert sensor.is_on is None
    assert sensor.extra_state_attributes == {}

    # No pet
    mock_coordinator_binary.data.getPet.return_value = None
    assert sensor.is_on is None
    assert sensor.device_info == {}


async def test_wifi_network_hidden_binary_sensor(
    hass: HomeAssistant, mock_coordinator_binary, mock_wifi_network
) -> None:
    """Test WiFi network hidden binary sensor."""
    sensor = TryFiWifiNetworkHiddenBinarySensor(
        mock_coordinator_binary, mock_wifi_network
    )

    assert sensor._attr_unique_id == "wifi-MyHomeWiFi-hidden"
    assert sensor._attr_name == "Hidden"
    assert sensor.is_on is False
    assert sensor.icon == "mdi:wifi"

    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, "wifi-MyHomeWiFi")}
    assert device_info["name"] == "WiFi MyHomeWiFi"
    assert device_info["manufacturer"] == MANUFACTURER
    assert device_info["model"] == "WiFi Network"

    # Test hidden WiFi
    mock_wifi_network.isHidden = True
    assert sensor.is_on is True
    assert sensor.icon == "mdi:wifi-off"

    # Test missing WiFi network from coordinator
    mock_coordinator_binary.data.getWifiNetwork.return_value = None
    assert sensor.network is None
    assert sensor.is_on is None
    assert sensor.device_info == {}
