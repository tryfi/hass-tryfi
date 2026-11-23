"""Tests for TryFi's Home Assistant diagnostics download."""

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.tryfi.const import CONF_POLLING_RATE, DOMAIN
from custom_components.tryfi.coordinator import TryFiDataUpdateCoordinator
from custom_components.tryfi.pytryfi import PyTryFi


async def test_diagnostics_download(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
):
    """Download support data without serializing credentials or personal values."""
    username = "canary-owner@example.invalid"
    password = "canary-password"
    token = "canary-session-token"
    pet_name = "canary-pet-name"
    owner_address = "canary-owner-address"
    pet_id = "canary-pet-id"
    collar_id = "canary-collar-id"
    ssid = "canary-wifi-ssid"
    latitude, longitude = 37.412345, -122.098765
    error_message = f"canary-api-error containing {token}"

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=username,
        unique_id=username,
        data={"username": username, "password": password, CONF_POLLING_RATE: 45},
        options={"token": token, "future_setting": owner_address},
    )
    entry.add_to_hass(hass)
    tryfi = Mock(spec=PyTryFi)
    tryfi.session = {"Authorization": token}
    tryfi.currentUser = SimpleNamespace(email=username, address=owner_address)
    tryfi.pets = [
        SimpleNamespace(
            name=pet_name,
            petId=pet_id,
            currLatitude=latitude,
            currLongitude=longitude,
            currPlaceName=owner_address,
            device=SimpleNamespace(
                deviceId=collar_id, batteryPercent=88, isCharging=True
            ),
        ),
        SimpleNamespace(
            name="canary-collarless-name", petId="canary-collarless-id", device=None
        ),
    ]
    tryfi.bases = [SimpleNamespace(name=owner_address, online=True)]
    tryfi.wifiNetworks = [SimpleNamespace(ssid=ssid, latitude=latitude)]
    tryfi.update.side_effect = [None] * 10 + [
        RuntimeError(error_message),
        None,
        RuntimeError(error_message),
    ]

    coordinator = TryFiDataUpdateCoordinator(hass, tryfi, polling_interval=45)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    # Platform discovery needs a loaded component. The mocked setup avoids API calls.
    with patch("custom_components.tryfi.async_setup_entry", return_value=True):
        assert await hass.config_entries.async_setup(entry.entry_id)
    for _ in range(13):
        await coordinator.async_refresh()

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert tryfi.update.call_count == 13
    payload = json.dumps(result, allow_nan=False)
    for canary in (
        username,
        password,
        token,
        pet_name,
        "canary-collarless-name",
        "canary-collarless-id",
        owner_address,
        pet_id,
        collar_id,
        ssid,
        str(latitude),
        str(longitude),
        error_message,
    ):
        assert canary not in payload

    assert result == {
        "config": {
            "entry_version": entry.version,
            "polling_interval_seconds": 45,
            "polling_disabled": False,
        },
        "coordinator": {
            "last_update_success": False,
            "last_exception_type": "RuntimeError",
            "recent_refresh_results": [True] * 7 + [False, True, False],
        },
        "devices": {
            "pet_count": 2,
            "collars": [{"battery_percent": 88, "charging": True}],
            "bases": [{"online": True}],
            "wifi_network_count": 1,
        },
    }


async def test_diagnostics_before_data(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
):
    """Return safe config with no coordinator, and preserve unknown poll data."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_POLLING_RATE: "canary-invalid-rate"}
    )
    entry.add_to_hass(hass)
    with patch("custom_components.tryfi.async_setup_entry", return_value=True):
        assert await hass.config_entries.async_setup(entry.entry_id)

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert result == {
        "config": {
            "entry_version": entry.version,
            "polling_interval_seconds": None,
            "polling_disabled": False,
        },
        "coordinator": None,
        "devices": None,
    }

    hass.data[DOMAIN] = {
        entry.entry_id: TryFiDataUpdateCoordinator(
            hass, Mock(spec=PyTryFi), polling_interval=60
        )
    }
    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert result["devices"] is None
    assert result["coordinator"] == {
        "last_update_success": None,
        "last_exception_type": None,
        "recent_refresh_results": [],
    }
