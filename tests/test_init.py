"""Test TryFi setup."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.tryfi import (
    TryFiDataUpdateCoordinator,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.tryfi.const import DOMAIN

from tests.common import MockConfigEntry


@pytest.fixture
def mock_pytryfi():
    """Mock PyTryFi."""
    with patch("custom_components.tryfi.PyTryFi") as mock_pytryfi:
        instance = mock_pytryfi.return_value
        instance.currentUser = Mock()
        instance.update = Mock()
        instance.pets = []
        instance.bases = []
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
    hass: HomeAssistant, mock_pytryfi, mock_config_entry
) -> None:
    """Test successful setup."""
    mock_config_entry.add_to_hass(hass)
    
    with patch(
        "custom_components.tryfi.TryFiDataUpdateCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = mock_coordinator_class.return_value
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        
        assert await async_setup_entry(hass, mock_config_entry)
        assert mock_config_entry.state == ConfigEntryState.LOADED
        
        # Verify coordinator was created and stored
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_setup_entry_auth_failed(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test setup when auth fails."""
    mock_config_entry.add_to_hass(hass)
    
    with patch("custom_components.tryfi.PyTryFi") as mock_pytryfi:
        # No currentUser attribute means auth failed
        mock_pytryfi.return_value = Mock(spec=[])
        
        with pytest.raises(ConfigEntryNotReady):
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


async def test_unload_entry(
    hass: HomeAssistant, mock_pytryfi, mock_config_entry
) -> None:
    """Test unloading entry."""
    mock_config_entry.add_to_hass(hass)
    
    # Setup entry first
    with patch(
        "custom_components.tryfi.TryFiDataUpdateCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = mock_coordinator_class.return_value
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        
        await async_setup_entry(hass, mock_config_entry)
        
        # Now unload
        assert await async_unload_entry(hass, mock_config_entry)
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]


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