"""Test TryFi setup."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.tryfi import (
    TryFiDataUpdateCoordinator,
    async_remove_config_entry_device,
    async_setup_entry,
    async_unload_entry,
    async_update_options,
)
from custom_components.tryfi.const import DOMAIN

from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture
def mock_pytryfi():
    """Mock PyTryFi."""
    with patch("custom_components.tryfi.PyTryFi") as mock_pytryfi:
        instance = mock_pytryfi.return_value
        instance.currentUser = Mock()
        instance.update = Mock()
        instance.pets = []
        instance.bases = []
        instance.wifiNetworks = []
        yield instance


@pytest.fixture
def mock_config_entry():
    """Mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test@email.com",
            "password": "test-password",
            "polling": 30,
        },
    )


async def test_setup_entry_success(
    hass: HomeAssistant, mock_config_entry, mock_pytryfi
) -> None:
    """Test successful setup entry flow."""
    mock_config_entry.add_to_hass(hass)
    mock_config_entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)

    with (
        patch("custom_components.tryfi.async_setup_services") as mock_setup_services,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", return_value=True
        ),
    ):
        result = await async_setup_entry(hass, mock_config_entry)
        assert result is True
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        mock_setup_services.assert_called_once_with(hass)


async def test_setup_entry_auth_failed(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test setup when auth fails (no currentUser or currentUser is None)."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.tryfi.PyTryFi") as mock_pytryfi:
        # No currentUser attribute means auth failed
        instance = Mock(spec=["pets", "bases", "wifiNetworks"])
        instance.pets = []
        instance.bases = []
        instance.wifiNetworks = []
        mock_pytryfi.return_value = instance

        with pytest.raises(ConfigEntryNotReady, match="Failed to authenticate with TryFi API"):
            await async_setup_entry(hass, mock_config_entry)

    with patch("custom_components.tryfi.PyTryFi") as mock_pytryfi:
        # currentUser is None means auth failed
        instance = Mock()
        instance.pets = []
        instance.bases = []
        instance.wifiNetworks = []
        instance.currentUser = None
        mock_pytryfi.return_value = instance

        with pytest.raises(ConfigEntryNotReady, match="Failed to authenticate with TryFi API"):
            await async_setup_entry(hass, mock_config_entry)


async def test_setup_entry_exception(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test setup when PyTryFi raises exception."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.tryfi.PyTryFi",
        side_effect=Exception("Connection failed"),
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


async def test_async_update_options(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test update options reloads config entry."""
    with patch.object(hass.config_entries, "async_reload") as mock_reload:
        await async_update_options(hass, mock_config_entry)
        mock_reload.assert_called_once_with(mock_config_entry.entry_id)


async def test_async_unload_entry_success(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test successful unload of config entry."""
    mock_config_entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = Mock()

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=True
    ):
        result = await async_unload_entry(hass, mock_config_entry)
        assert result is True
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]


async def test_async_unload_entry_failure(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test failed unload of config entry."""
    mock_config_entry.add_to_hass(hass)
    mock_coordinator = Mock()
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = mock_coordinator

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=False
    ):
        result = await async_unload_entry(hass, mock_config_entry)
        assert result is False
        assert hass.data[DOMAIN][mock_config_entry.entry_id] == mock_coordinator


async def test_async_remove_config_entry_device_base_station_name(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test removing device with 'Base Station' in name."""
    device_entry = Mock()
    device_entry.name = "Living Room Base Station"
    device_entry.model = "TryFi Base V2"
    device_entry.identifiers = {(DOMAIN, "base_123")}

    result = await async_remove_config_entry_device(
        hass, mock_config_entry, device_entry
    )
    assert result is True


async def test_async_remove_config_entry_device_old_format_model(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test removing device with model 'TryFi Base'."""
    device_entry = Mock()
    device_entry.name = "Living Room Base"
    device_entry.model = "TryFi Base"
    device_entry.identifiers = {(DOMAIN, "base_123")}

    result = await async_remove_config_entry_device(
        hass, mock_config_entry, device_entry
    )
    assert result is True


async def test_async_remove_config_entry_device_old_format_base_prefix(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test removing device with identifier starting with base_."""
    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.pets = []
    coordinator.data.bases = []
    coordinator.data.wifiNetworks = []
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coordinator

    device_entry = Mock()
    device_entry.name = "Living Room Charger"
    device_entry.model = "Charger V1"
    device_entry.identifiers = {(DOMAIN, "base_12345")}

    result = await async_remove_config_entry_device(
        hass, mock_config_entry, device_entry
    )
    assert result is True


async def test_async_remove_config_entry_device_inactive(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test removing device that is no longer in API data."""
    pet_mock = Mock(petId="pet_active")
    base_mock = Mock(baseId="base_active")
    wifi_mock = Mock(ssid="wifi_active")

    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.pets = [pet_mock]
    coordinator.data.bases = [base_mock]
    coordinator.data.wifiNetworks = [wifi_mock]
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coordinator

    device_entry = Mock()
    device_entry.name = "Old Pet Collar"
    device_entry.model = "Collar V1"
    device_entry.identifiers = {(DOMAIN, "pet_inactive")}

    result = await async_remove_config_entry_device(
        hass, mock_config_entry, device_entry
    )
    assert result is True


async def test_async_remove_config_entry_device_active(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test removing device that is still active in API data."""
    pet_mock = Mock(petId="pet_active")
    base_mock = Mock(baseId="active_base_123")
    wifi_mock = Mock(ssid="home_wifi")

    coordinator = Mock()
    coordinator.data = Mock()
    coordinator.data.pets = [pet_mock]
    coordinator.data.bases = [base_mock]
    coordinator.data.wifiNetworks = [wifi_mock]
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coordinator

    # Check pet active device
    pet_device = Mock()
    pet_device.name = "Active Pet"
    pet_device.model = "Collar"
    pet_device.identifiers = {(DOMAIN, "pet_active")}
    assert (
        await async_remove_config_entry_device(hass, mock_config_entry, pet_device)
        is False
    )

    # Check base active device
    base_device = Mock()
    base_device.name = "Active Base"
    base_device.model = "Base"
    base_device.identifiers = {(DOMAIN, "active_base_123")}
    assert (
        await async_remove_config_entry_device(hass, mock_config_entry, base_device)
        is False
    )

    # Check wifi active device
    wifi_device = Mock()
    wifi_device.name = "Active WiFi"
    wifi_device.model = "WiFi"
    wifi_device.identifiers = {(DOMAIN, "wifi-home_wifi")}
    assert (
        await async_remove_config_entry_device(hass, mock_config_entry, wifi_device)
        is False
    )


async def test_async_remove_config_entry_device_exception(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test error handling in device removal (allows removal)."""
    # No entry in hass.data[DOMAIN], causing KeyError in coordinator access
    hass.data.setdefault(DOMAIN, {})

    device_entry = Mock()
    device_entry.name = "Error Device"
    device_entry.model = "Collar"
    device_entry.identifiers = {(DOMAIN, "device_err")}

    result = await async_remove_config_entry_device(
        hass, mock_config_entry, device_entry
    )
    assert result is True


async def test_coordinator_update_success(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test coordinator update success."""
    coordinator = TryFiDataUpdateCoordinator(hass, mock_pytryfi, 30)

    result = await coordinator._async_update_data()

    assert result == mock_pytryfi
    mock_pytryfi.update.assert_called_once()


async def test_coordinator_update_failure(
    hass: HomeAssistant, mock_pytryfi
) -> None:
    """Test coordinator update failure."""
    mock_pytryfi.update.side_effect = Exception("API Error")

    coordinator = TryFiDataUpdateCoordinator(hass, mock_pytryfi, 30)

    with pytest.raises(Exception, match="API Error"):
        await coordinator._async_update_data()
