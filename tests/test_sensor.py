"""Test TryFi sensor platform."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from custom_components.tryfi.const import DOMAIN
from custom_components.tryfi.sensor import (
    PetBehaviorSensor,
    PetGenericSensor,
    PetSleepQualitySensor,
    PetStatsSensor,
    TryFiBaseDiagnosticSensor,
    TryFiBaseSensor,
    TryFiBatterySensor,
    TryFiWifiNetworkSensor,
    async_setup_entry,
    icon_for_battery_level,
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
    pet.breed = "Labrador"
    pet.photoLink = "https://example.com/photo.jpg"
    pet.activityType = "REST"
    pet.currPlaceName = "Home"
    pet.currPlaceAddress = "123 Main St"
    pet.gender = "Male"
    pet.weight = 30.5
    pet.yearOfBirth = 2020
    pet.device = Mock()
    pet.device.batteryPercent = 75
    pet.device.isCharging = False
    pet.device.connectedTo = "ConnectedToCellular"
    pet.device.connectionStateType = "Cellular"
    pet.device.connectionSignalStrength = -85.0
    pet.device.ledColor = "RED"
    pet.device.moduleId = "mod_123"
    pet.dailySteps = 5000
    pet.weeklyTotalDistance = 17500
    pet.monthlySleep = 864000
    pet.dailySleep = 48000  # 800 minutes
    pet.dailyNap = 6000     # 100 minutes
    pet.dailyBarkingCount = 5
    return pet


@pytest.fixture
def mock_base():
    """Create a mock base."""
    base = Mock()
    base.baseId = "base_123"
    base.name = "Living Room Base"
    base.online = True
    base.onlineQuality = "HEALTHY"
    base.networkname = "HomeWiFi"
    base.lastUpdated = "2023-01-01T00:00:00Z"
    return base


@pytest.fixture
def mock_wifi_network():
    """Create a mock wifi network."""
    network = Mock()
    network.ssid = "HomeWiFi"
    network.state = "Connected"
    network.addressLabel = "Home Network"
    return network


@pytest.fixture
def mock_coordinator_sensor(mock_pet_with_stats, mock_base, mock_wifi_network):
    """Create a mock coordinator for sensor tests."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.pets = [mock_pet_with_stats]
    coordinator.data.bases = [mock_base]
    coordinator.data.wifiNetworks = [mock_wifi_network]
    coordinator.data.getPet = Mock(return_value=mock_pet_with_stats)
    coordinator.data.getBase = Mock(return_value=mock_base)
    coordinator.data.getWifiNetwork = Mock(return_value=mock_wifi_network)
    coordinator.async_add_listener = Mock(return_value=Mock())
    return coordinator


async def test_async_setup_entry(
    hass: HomeAssistant, mock_coordinator_sensor
) -> None:
    """Test setup entry for TryFi sensors."""
    config_entry = Mock()
    config_entry.entry_id = "test_entry"
    config_entry.async_on_unload = Mock()

    hass.data = {DOMAIN: {"test_entry": mock_coordinator_sensor}}

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    assert async_add_entities.called
    added_entities = async_add_entities.call_args[0][0]
    assert len(added_entities) > 0

    # Verify WifiNetworkSensors are created
    wifi_sensors = [e for e in added_entities if isinstance(e, TryFiWifiNetworkSensor)]
    assert len(wifi_sensors) == 2

    # Test coordinator listener callback for new WiFi networks
    assert mock_coordinator_sensor.async_add_listener.called
    listener_cb = mock_coordinator_sensor.async_add_listener.call_args[0][0]

    # Add new wifi network to coordinator data
    new_wifi = Mock()
    new_wifi.ssid = "NewNetwork"
    new_wifi.state = "Available"
    new_wifi.addressLabel = "New Addr"
    mock_coordinator_sensor.data.wifiNetworks.append(new_wifi)

    async_add_entities.reset_mock()
    listener_cb()

    assert async_add_entities.called
    new_added = async_add_entities.call_args[0][0]
    assert len(new_added) == 2
    assert all(isinstance(e, TryFiWifiNetworkSensor) for e in new_added)


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
    """Test TryFi generic sensor with all keys."""
    mock_coordinator.data.getPet.return_value = mock_pet_with_stats

    # Test activity type sensor
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "activity_type")
    assert sensor.unique_id == "test_pet_123-activity-type"
    assert sensor.name == "Fido Activity Type"
    assert sensor.native_value == "REST"
    assert sensor.icon == "mdi:run"

    # Test current place name
    sensor = PetGenericSensor(
        mock_coordinator, mock_pet_with_stats, "current_place_name"
    )
    assert sensor.unique_id == "test_pet_123-current-place-name"
    assert sensor.name == "Fido Current Place Name"
    assert sensor.native_value == "Home"
    assert sensor.icon == "mdi:map-marker"

    # Test current place address
    sensor = PetGenericSensor(
        mock_coordinator, mock_pet_with_stats, "current_place_address"
    )
    assert sensor.native_value == "123 Main St"

    # Test connected_to
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "connected_to")
    assert sensor.unique_id == "test_pet_123-connected-to"
    assert sensor.name == "Fido Connected To"
    assert sensor.native_value == "ConnectedToCellular"
    assert sensor.icon == "mdi:wifi"

    # Test gender
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "gender")
    assert sensor.native_value == "Male"

    # Test weight
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "weight")
    assert sensor.native_value == 30.5

    # Test age (with yearOfBirth)
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "age")
    assert isinstance(sensor.native_value, int)
    assert sensor.native_value > 0

    # Test age (without yearOfBirth)
    mock_pet_with_stats.yearOfBirth = None
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "age")
    assert sensor.native_value is None

    # Test connection_state
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "connection_state")
    assert sensor.native_value == "Cellular"

    # Test led_color
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "led_color")
    assert sensor.native_value == "RED"

    # Test module_id
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "module_id")
    assert sensor.native_value == "mod_123"

    # Test signal_strength (cellular)
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "signal_strength")
    assert sensor.native_value == -85.0

    # Test signal_strength (not cellular)
    mock_pet_with_stats.device.connectedTo = "WiFi"
    assert sensor.native_value is None

    # Test unknown key
    sensor = PetGenericSensor(mock_coordinator, mock_pet_with_stats, "unknown_key")
    assert sensor.native_value is None


async def test_base_sensor(hass: HomeAssistant, mock_coordinator, mock_base) -> None:
    """Test TryFi base station sensor."""
    mock_coordinator.data.getBase.return_value = mock_base

    sensor = TryFiBaseSensor(mock_coordinator, mock_base)

    assert sensor.unique_id == "base_123"
    assert sensor.name == "Living Room Base"
    assert sensor.native_value == "Online"
    assert sensor.icon == "mdi:home-circle"
    assert sensor.device_info["identifiers"] == {(DOMAIN, "base_123")}

    attrs = sensor.extra_state_attributes
    assert attrs["wifi_network"] == "HomeWiFi"
    assert attrs["connection_quality"] == "HEALTHY"
    assert attrs["last_updated"] == "2023-01-01T00:00:00Z"

    # Test unhealthy online quality
    mock_base.onlineQuality = "UNHEALTHY"
    assert sensor.native_value == "Unhealthy"

    # Test offline base
    mock_base.online = False
    assert sensor.native_value == "Offline"

    # Test base missing from coordinator
    mock_coordinator.data.getBase.return_value = None
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


async def test_base_diagnostic_sensor(
    hass: HomeAssistant, mock_coordinator, mock_base
) -> None:
    """Test TryFi base diagnostic sensor."""
    mock_coordinator.data.getBase.return_value = mock_base

    # Test WiFi SSID
    sensor = TryFiBaseDiagnosticSensor(mock_coordinator, mock_base, "WiFi SSID")
    assert sensor._attr_unique_id == "base_123-wifi-ssid"
    assert sensor.name == "Living Room Base WiFi SSID"
    assert sensor.native_value == "HomeWiFi"
    assert sensor.icon == "mdi:wifi"
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC

    # Test Base ID
    sensor = TryFiBaseDiagnosticSensor(mock_coordinator, mock_base, "Base ID")
    assert sensor.native_value == "base_123"
    assert sensor.icon == "mdi:identifier"

    # Test Connection Quality
    sensor = TryFiBaseDiagnosticSensor(
        mock_coordinator, mock_base, "Connection Quality"
    )
    assert sensor.native_value == "HEALTHY"
    assert sensor.icon == "mdi:signal"

    # Test Unknown Key
    sensor = TryFiBaseDiagnosticSensor(mock_coordinator, mock_base, "Unknown Key")
    assert sensor.native_value is None
    assert sensor.icon == "mdi:information"

    # Test base missing from coordinator
    mock_coordinator.data.getBase.return_value = None
    assert sensor.native_value is None


async def test_sensor_no_data(hass: HomeAssistant, mock_coordinator) -> None:
    """Test sensors when no data is available."""
    mock_coordinator.data.getPet.return_value = None

    mock_pet = Mock()
    mock_pet.petId = "test_pet"
    mock_pet.name = "Test"

    sensor = TryFiBatterySensor(mock_coordinator, mock_pet)
    assert sensor.native_value is None

    sensor = PetStatsSensor(mock_coordinator, mock_pet, "STEPS", "DAILY")
    assert sensor.native_value is None

    sensor = PetGenericSensor(mock_coordinator, mock_pet, "Activity Type")
    assert sensor.native_value is None

    sensor = PetSleepQualitySensor(mock_coordinator, mock_pet)
    assert sensor.native_value is None


async def test_sleep_quality_sensor_calculations(
    hass: HomeAssistant, mock_coordinator, mock_pet_with_stats
) -> None:
    """Test PetSleepQualitySensor score calculations."""
    mock_coordinator.data.getPet.return_value = mock_pet_with_stats

    # total_rest = 48000/60 + 6000/60 = 800 + 100 = 900 minutes (>= optimal_rest 780)
    sensor = PetSleepQualitySensor(mock_coordinator, mock_pet_with_stats)
    assert sensor.unique_id == "test_pet_123-sleep-quality"
    assert sensor.name == "Fido Sleep Quality Score"
    assert sensor.native_value > 80

    # Test None values for sleep and nap
    mock_pet_with_stats.dailySleep = None
    mock_pet_with_stats.dailyNap = None
    assert sensor.native_value == 0


async def test_pet_behavior_sensor(
    hass: HomeAssistant, mock_coordinator, mock_pet_with_stats
) -> None:
    """Test PetBehaviorSensor."""
    mock_coordinator.data.getPet.return_value = mock_pet_with_stats

    # Test barking count
    sensor = PetBehaviorSensor(
        mock_coordinator, mock_pet_with_stats, "barking", "count", "daily"
    )
    assert sensor._attr_unique_id == "tryfi-pet-test_pet_123-daily-barking-count"
    assert sensor.name == "Fido Daily Barking Count"
    assert sensor.native_value == 5
    assert sensor.icon == "mdi:dog"
    assert sensor.native_unit_of_measurement == "events"

    # Test barking duration
    mock_pet_with_stats.dailyBarkingDuration = 120
    sensor = PetBehaviorSensor(
        mock_coordinator, mock_pet_with_stats, "barking", "duration", "daily"
    )
    assert sensor.native_value == 120
    assert sensor.native_unit_of_measurement == UnitOfTime.MINUTES
    assert sensor.device_class == SensorDeviceClass.DURATION

    # Test missing attribute returns 0
    delattr(mock_pet_with_stats, "dailyBarkingCount")
    sensor = PetBehaviorSensor(
        mock_coordinator, mock_pet_with_stats, "barking", "count", "daily"
    )
    assert sensor.native_value == 0

    # Test pet missing from coordinator
    mock_coordinator.data.getPet.return_value = None
    assert sensor.native_value is None


async def test_wifi_network_sensor(
    hass: HomeAssistant, mock_coordinator_sensor, mock_wifi_network
) -> None:
    """Test TryFi WiFi network sensor."""
    # Test Status sensor
    sensor = TryFiWifiNetworkSensor(
        mock_coordinator_sensor, mock_wifi_network, "Status"
    )
    assert sensor._attr_unique_id == "wifi-HomeWiFi-status"
    assert sensor.name == "Status"
    assert sensor.icon == "mdi:wifi-settings"
    assert sensor.native_value == "Connected"

    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, "wifi-HomeWiFi")}
    assert device_info["name"] == "WiFi HomeWiFi"

    # Test Address sensor
    sensor = TryFiWifiNetworkSensor(
        mock_coordinator_sensor, mock_wifi_network, "Address"
    )
    assert sensor._attr_unique_id == "wifi-HomeWiFi-address"
    assert sensor.name == "Address"
    assert sensor.icon == "mdi:map-marker-outline"
    assert sensor.native_value == "Home Network"

    # Test unknown sensor type
    sensor = TryFiWifiNetworkSensor(
        mock_coordinator_sensor, mock_wifi_network, "Unknown"
    )
    assert sensor.native_value is None

    # Test network missing from coordinator
    mock_coordinator_sensor.data.getWifiNetwork.return_value = None
    assert sensor.network is None
    assert sensor.native_value is None
    assert sensor.device_info == {}


def test_icon_for_battery_level_coverage():
    """Test icon_for_battery_level function for all battery ranges."""
    assert icon_for_battery_level(None) == "mdi:battery-unknown"
    assert icon_for_battery_level(50, charging=True) == "mdi:battery-charging"
    assert icon_for_battery_level(95) == "mdi:battery"
    assert icon_for_battery_level(80) == "mdi:battery-80"
    assert icon_for_battery_level(60) == "mdi:battery-60"
    assert icon_for_battery_level(40) == "mdi:battery-40"
    assert icon_for_battery_level(20) == "mdi:battery-20"
    assert icon_for_battery_level(5) == "mdi:battery-alert"
