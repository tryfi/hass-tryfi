"""Diagnostics for the TryFi integration."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_POLLING_RATE, DEFAULT_POLLING_RATE, DOMAIN
from .coordinator import TryFiDataUpdateCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return an allowlisted snapshot of configuration and cached polling state."""
    polling_rate = entry.data.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE)
    diagnostics: dict[str, Any] = {
        "config": {
            "entry_version": entry.version,
            "polling_interval_seconds": (
                polling_rate
                if type(polling_rate) is int and 10 <= polling_rate <= 3600
                else None
            ),
            "polling_disabled": entry.pref_disable_polling,
        },
        "coordinator": None,
        "devices": None,
    }

    coordinator: TryFiDataUpdateCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if coordinator is None:
        return diagnostics

    # Export only the exception class. Messages may contain request or account data.
    last_exception = (
        coordinator.last_exception if not coordinator.last_update_success else None
    )
    if last_exception is not None and last_exception.__cause__ is not None:
        last_exception = last_exception.__cause__
    diagnostics["coordinator"] = {
        "last_update_success": (
            coordinator.last_update_success
            if coordinator.recent_refresh_results
            else None
        ),
        "last_exception_type": (
            type(last_exception).__name__ if last_exception is not None else None
        ),
        "recent_refresh_results": list(coordinator.recent_refresh_results),
    }

    data = coordinator.data
    if data is None:
        return diagnostics

    # Project only numeric and boolean state. Never export raw API or registry objects.
    pets = data.pets
    collars = []
    for pet in pets:
        collar = pet.device
        if collar is None:
            continue
        battery = collar.batteryPercent
        charging = collar.isCharging
        collars.append(
            {
                "battery_percent": (
                    battery if type(battery) is int and 0 <= battery <= 100 else None
                ),
                "charging": charging if type(charging) is bool else None,
            }
        )

    bases = []
    for base in data.bases:
        online = base.online
        bases.append({"online": online if type(online) is bool else None})

    diagnostics["devices"] = {
        "pet_count": len(pets),
        "collars": collars,
        "bases": bases,
        "wifi_network_count": len(data.wifiNetworks),
    }
    return diagnostics
