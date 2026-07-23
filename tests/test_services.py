"""Test TryFi registered services."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.tryfi import (
    TryFiDataUpdateCoordinator,
    async_setup_services,
)
from custom_components.tryfi.const import DOMAIN


@pytest.fixture
async def setup_services(hass: HomeAssistant):
    """Register TryFi services."""
    await async_setup_services(hass)


@pytest.fixture
def mock_pet():
    """Create a mock pet."""
    pet = Mock()
    pet.name = "Fido"
    pet.setLedColorCode = Mock()
    pet.turnOnOffLed = Mock()
    pet.setLostDogMode = Mock()
    return pet


@pytest.fixture
def mock_wifi_network():
    """Create a mock wifi network."""
    network = Mock()
    network.ssid = "HomeWifi"
    return network


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_pet, mock_wifi_network):
    """Create a mock coordinator with data."""
    coordinator = TryFiDataUpdateCoordinator(hass, Mock(), 30)
    coordinator.data = Mock()
    coordinator.data.session = "mock_session"
    coordinator.data.pets = [mock_pet]
    coordinator.data.getWifiNetwork = Mock(
        side_effect=lambda ssid: mock_wifi_network if ssid == "HomeWifi" else None
    )
    coordinator.data.setWifiNetworkLocation = Mock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def test_set_led_color_valid(
    hass: HomeAssistant, setup_services, mock_coordinator, mock_pet
) -> None:
    """Test set_led_color service with valid color."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    await hass.services.async_call(
        DOMAIN,
        "set_led_color",
        {"entity_id": "light.fido_collar_light", "color": "red"},
        blocking=True,
    )

    mock_pet.setLedColorCode.assert_called_once_with(
        mock_coordinator.data.session, 1
    )
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_set_led_color_invalid_color_fallback(
    hass: HomeAssistant, setup_services, mock_coordinator, mock_pet
) -> None:
    """Test set_led_color service falls back to white (8) for unknown colors."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    await hass.services.async_call(
        DOMAIN,
        "set_led_color",
        {"entity_id": "light.fido_collar_light", "color": "unknown_color"},
        blocking=True,
    )

    mock_pet.setLedColorCode.assert_called_once_with(
        mock_coordinator.data.session, 8
    )
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_set_led_color_missing_entity_id(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test set_led_color service without entity_id raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(HomeAssistantError, match="No entity_id provided"):
        await hass.services.async_call(
            DOMAIN,
            "set_led_color",
            {"color": "red"},
            blocking=True,
        )


async def test_set_led_color_pet_not_found(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test set_led_color service with non-existent pet entity raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(
        HomeAssistantError, match="Pet not found for entity light.nonexistent_collar_light"
    ):
        await hass.services.async_call(
            DOMAIN,
            "set_led_color",
            {"entity_id": "light.nonexistent_collar_light", "color": "red"},
            blocking=True,
        )


async def test_turn_on_led_valid(
    hass: HomeAssistant, setup_services, mock_coordinator, mock_pet
) -> None:
    """Test turn_on_led service with valid entity."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    await hass.services.async_call(
        DOMAIN,
        "turn_on_led",
        {"entity_id": "light.fido_collar_light"},
        blocking=True,
    )

    mock_pet.turnOnOffLed.assert_called_once_with(
        mock_coordinator.data.session, True
    )
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_turn_on_led_missing_entity_id(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test turn_on_led service without entity_id raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(HomeAssistantError, match="No entity_id provided"):
        await hass.services.async_call(
            DOMAIN,
            "turn_on_led",
            {},
            blocking=True,
        )


async def test_turn_on_led_pet_not_found(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test turn_on_led service with non-existent pet entity raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(
        HomeAssistantError, match="Pet not found for entity light.nonexistent_collar_light"
    ):
        await hass.services.async_call(
            DOMAIN,
            "turn_on_led",
            {"entity_id": "light.nonexistent_collar_light"},
            blocking=True,
        )


async def test_turn_off_led_valid(
    hass: HomeAssistant, setup_services, mock_coordinator, mock_pet
) -> None:
    """Test turn_off_led service with valid entity."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    await hass.services.async_call(
        DOMAIN,
        "turn_off_led",
        {"entity_id": "light.fido_collar_light"},
        blocking=True,
    )

    mock_pet.turnOnOffLed.assert_called_once_with(
        mock_coordinator.data.session, False
    )
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_turn_off_led_missing_entity_id(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test turn_off_led service without entity_id raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(HomeAssistantError, match="No entity_id provided"):
        await hass.services.async_call(
            DOMAIN,
            "turn_off_led",
            {},
            blocking=True,
        )


async def test_turn_off_led_pet_not_found(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test turn_off_led service with non-existent pet entity raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(
        HomeAssistantError, match="Pet not found for entity light.nonexistent_collar_light"
    ):
        await hass.services.async_call(
            DOMAIN,
            "turn_off_led",
            {"entity_id": "light.nonexistent_collar_light"},
            blocking=True,
        )


async def test_set_lost_mode_lost(
    hass: HomeAssistant, setup_services, mock_coordinator, mock_pet
) -> None:
    """Test set_lost_mode service with mode 'Lost'."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    await hass.services.async_call(
        DOMAIN,
        "set_lost_mode",
        {"entity_id": "select.fido_lost_mode", "mode": "Lost"},
        blocking=True,
    )

    mock_pet.setLostDogMode.assert_called_once_with(
        mock_coordinator.data.session, True
    )
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_set_lost_mode_safe(
    hass: HomeAssistant, setup_services, mock_coordinator, mock_pet
) -> None:
    """Test set_lost_mode service with mode 'Safe'."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    await hass.services.async_call(
        DOMAIN,
        "set_lost_mode",
        {"entity_id": "select.fido_lost_mode", "mode": "Safe"},
        blocking=True,
    )

    mock_pet.setLostDogMode.assert_called_once_with(
        mock_coordinator.data.session, False
    )
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_set_lost_mode_missing_entity_id(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test set_lost_mode service without entity_id raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(HomeAssistantError, match="No entity_id provided"):
        await hass.services.async_call(
            DOMAIN,
            "set_lost_mode",
            {"mode": "Lost"},
            blocking=True,
        )


async def test_set_lost_mode_pet_not_found(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test set_lost_mode service with non-existent pet entity raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(
        HomeAssistantError, match="Pet not found for entity select.nonexistent_lost_mode"
    ):
        await hass.services.async_call(
            DOMAIN,
            "set_lost_mode",
            {"entity_id": "select.nonexistent_lost_mode", "mode": "Lost"},
            blocking=True,
        )


async def test_set_wifi_location_valid(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test set_wifi_location service with valid parameters."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    await hass.services.async_call(
        DOMAIN,
        "set_wifi_location",
        {"ssid": "HomeWifi", "latitude": 37.7749, "longitude": -122.4194},
        blocking=True,
    )

    mock_coordinator.data.setWifiNetworkLocation.assert_called_once_with(
        "HomeWifi", 37.7749, -122.4194
    )
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_set_wifi_location_missing_ssid(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test set_wifi_location service without ssid raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(HomeAssistantError, match="No ssid provided"):
        await hass.services.async_call(
            DOMAIN,
            "set_wifi_location",
            {"latitude": 37.7749, "longitude": -122.4194},
            blocking=True,
        )


async def test_set_wifi_location_missing_lat_lon(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test set_wifi_location service with missing latitude or longitude raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(
        HomeAssistantError, match="Both latitude and longitude are required"
    ):
        await hass.services.async_call(
            DOMAIN,
            "set_wifi_location",
            {"ssid": "HomeWifi", "latitude": 37.7749},
            blocking=True,
        )

    with pytest.raises(
        HomeAssistantError, match="Both latitude and longitude are required"
    ):
        await hass.services.async_call(
            DOMAIN,
            "set_wifi_location",
            {"ssid": "HomeWifi", "longitude": -122.4194},
            blocking=True,
        )


async def test_set_wifi_location_network_not_found(
    hass: HomeAssistant, setup_services, mock_coordinator
) -> None:
    """Test set_wifi_location service with non-existent SSID raises HomeAssistantError."""
    hass.data.setdefault(DOMAIN, {})["entry_id"] = mock_coordinator

    with pytest.raises(
        HomeAssistantError, match="WiFi network not found: NonExistentSSID"
    ):
        await hass.services.async_call(
            DOMAIN,
            "set_wifi_location",
            {"ssid": "NonExistentSSID", "latitude": 37.7749, "longitude": -122.4194},
            blocking=True,
        )
