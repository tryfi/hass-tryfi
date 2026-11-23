"""Tests for TryFi's Home Assistant diagnostics platform."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tryfi.const import CONF_POLLING_RATE, DOMAIN
from custom_components.tryfi.coordinator import TryFiDataUpdateCoordinator
from custom_components.tryfi import pytryfi
from custom_components.tryfi.pytryfi import FiPet, PyTryFi
from custom_components.tryfi.pytryfi.common import query


async def _get_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    """Load the diagnostics platform and call its config-entry hook without HTTP."""
    integration = await async_get_integration(hass, entry.domain)
    platform = await integration.async_get_platform("diagnostics")
    return await platform.async_get_config_entry_diagnostics(hass, entry)


async def test_diagnostics_payload(hass: HomeAssistant):
    """Return support data without serializing credentials or personal values."""
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
    tryfi.refresh_status = {}
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
    for _ in range(13):
        await coordinator.async_refresh()

    result = await _get_diagnostics(hass, entry)
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
            "updates": {},
        },
        "devices": {
            "pet_count": 2,
            "collars": [{"battery_percent": 88, "charging": True}],
            "bases": [{"online": True}],
            "wifi_network_count": 1,
        },
    }


async def test_diagnostics_before_data(hass: HomeAssistant):
    """Return safe config with no coordinator, and preserve unknown poll data."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_POLLING_RATE: "canary-invalid-rate"}
    )
    entry.add_to_hass(hass)

    result = await _get_diagnostics(hass, entry)
    assert result == {
        "config": {
            "entry_version": entry.version,
            "polling_interval_seconds": "canary-invalid-rate",
            "polling_disabled": False,
        },
        "coordinator": None,
        "devices": None,
    }

    hass.data[DOMAIN] = {
        entry.entry_id: TryFiDataUpdateCoordinator(
            hass, Mock(spec=PyTryFi, refresh_status={}), polling_interval=60
        )
    }
    result = await _get_diagnostics(hass, entry)
    assert result["devices"] is None
    assert result["coordinator"] == {
        "last_update_success": None,
        "last_exception_type": None,
        "recent_refresh_results": [],
        "updates": {},
    }


async def test_diagnostics_reports_partial_refreshes_and_recovery(
    hass: HomeAssistant,
):
    """Track caught API failures and recovery independently with a fake clock."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_POLLING_RATE: -1})
    entry.add_to_hass(hass)
    with (
        patch.object(PyTryFi, "login", autospec=True) as login,
        patch.object(
            pytryfi,
            "getHouseHolds",
            return_value={
                "email": "",
                "firstName": "",
                "lastName": "",
                "phoneNumber": "",
                "userHouseholds": [],
            },
        ),
    ):
        login.side_effect = lambda client, *_: setattr(client, "_userId", "synthetic")
        tryfi = PyTryFi()
    pet = FiPet("synthetic-pet")
    pet._device = Mock()
    pet._device.supportsAdvancedBehaviorStats.return_value = True
    pet._device.batteryPercent = 0
    tryfi._pets = [pet]
    tryfi._householdIds = ["synthetic-first", "synthetic-second"]
    coordinator = TryFiDataUpdateCoordinator(hass, tryfi, polling_interval=60)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    start = datetime(2025, 1, 1, tzinfo=UTC)
    moments = [start + timedelta(minutes=minute) for minute in range(4)]
    detail = dict.fromkeys(
        [
            "device",
            "ongoingActivity",
            "dailyStepStat",
            "weeklyStepStat",
            "monthlyStepStat",
            "dailySleepStat",
            "weeklySleepStat",
            "monthlySleepStat",
        ],
        {},
    )
    marker = "synthetic-private-api-error"
    with (
        patch.object(pytryfi, "datetime") as clock,
        patch.object(pytryfi, "getBaseList") as bases,
        patch.object(pytryfi, "getWifiNetworks") as wifi,
        patch.object(query, "getPetAllInfo") as pets,
        patch.object(query, "getPetHealthTrends") as behavior,
        patch.object(pet, "setCurrentLocation"),
        patch.object(pet, "setStats"),
    ):
        clock.now.return_value = moments[0]
        bases.return_value = []
        pets.return_value = detail
        wifi.return_value = {}
        behavior.return_value = {}
        await coordinator.async_refresh()
        result = await _get_diagnostics(hass, entry)
        assert result["config"]["polling_interval_seconds"] == -1
        assert result["devices"]["collars"][0]["battery_percent"] == 0
        expected = {
            "status": "success",
            "last_attempt_at": moments[0].isoformat(),
            "last_success_at": moments[0].isoformat(),
            "error_type": None,
        }
        areas = ("pets", "bases", "wifi", "behavior_stats")
        assert result["coordinator"]["updates"] == dict.fromkeys(areas, expected)

        clock.now.return_value = moments[1]
        bases.side_effect = ValueError(marker)
        wifi.side_effect = [TimeoutError(marker), {}]
        behavior.side_effect = [{}, RuntimeError(marker), {}]
        await coordinator.async_refresh()
        result = await _get_diagnostics(hass, entry)
        updates = result["coordinator"]["updates"]
        assert result["coordinator"]["last_update_success"] is True
        assert marker not in json.dumps(result)
        assert "synthetic-pet" not in json.dumps(result)
        assert "synthetic-first" not in json.dumps(result)
        assert updates["pets"] == {
            **expected,
            "last_attempt_at": moments[1].isoformat(),
            "last_success_at": moments[1].isoformat(),
        }
        for area, error_type in (
            ("bases", "ValueError"),
            ("wifi", "TimeoutError"),
            ("behavior_stats", "RuntimeError"),
        ):
            assert updates[area] == {
                **expected,
                "status": "error",
                "last_attempt_at": moments[1].isoformat(),
                "error_type": error_type,
            }

        clock.now.return_value = moments[2]
        pets.side_effect = LookupError(marker)
        wifi.side_effect = None
        bases.side_effect = None
        await coordinator.async_refresh()
        result = await _get_diagnostics(hass, entry)
        updates = result["coordinator"]["updates"]
        assert updates["pets"]["error_type"] == "LookupError"
        assert updates["pets"]["last_success_at"] == moments[1].isoformat()
        assert updates["behavior_stats"] == {
            **expected,
            "status": "skipped",
            "last_attempt_at": moments[1].isoformat(),
        }

        clock.now.return_value = moments[3]
        pets.side_effect = None
        behavior.side_effect = None
        await coordinator.async_refresh()
        result = await _get_diagnostics(hass, entry)
        assert result["coordinator"]["updates"] == dict.fromkeys(
            areas,
            {
                **expected,
                "last_attempt_at": moments[3].isoformat(),
                "last_success_at": moments[3].isoformat(),
            },
        )
