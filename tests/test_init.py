"""Test TryFi setup."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.tryfi import (
    TryFiDataUpdateCoordinator,
    async_setup_entry,
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


async def test_setup_entry_auth_failed(hass: HomeAssistant, mock_config_entry) -> None:
    """Test setup when auth fails."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.tryfi.PyTryFi") as mock_pytryfi:
        # No currentUser attribute means auth failed
        mock_pytryfi.return_value = Mock(spec=[])

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


async def test_setup_entry_exception(hass: HomeAssistant, mock_config_entry) -> None:
    """Test setup when PyTryFi raises exception."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.tryfi.PyTryFi",
        side_effect=Exception("Connection failed"),
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


async def test_coordinator_update_success(hass: HomeAssistant, mock_pytryfi) -> None:
    """Test coordinator update success."""
    coordinator = TryFiDataUpdateCoordinator(hass, mock_pytryfi, 30)

    result = await coordinator._async_update_data()

    assert result == mock_pytryfi
    mock_pytryfi.update.assert_called_once()


async def test_coordinator_update_failure(hass: HomeAssistant, mock_pytryfi) -> None:
    """Test coordinator update failure."""
    mock_pytryfi.update.side_effect = Exception("API Error")

    coordinator = TryFiDataUpdateCoordinator(hass, mock_pytryfi, 30)

    with pytest.raises(Exception, match="API Error"):
        await coordinator._async_update_data()
