"""The TryFi integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .coordinator import TryFiDataUpdateCoordinator

from .const import (
    CONF_PASSWORD,
    CONF_POLLING_RATE,
    CONF_USERNAME,
    DEFAULT_POLLING_RATE,
    DOMAIN,
)
from .pytryfi import PyTryFi

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TryFi from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    polling_interval = int(entry.data.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE))
    
    # Initialize the TryFi API client
    try:
        tryfi = await hass.async_add_executor_job(PyTryFi, username, password)
        _LOGGER.info(
            "TryFi API initialized: %d pets, %d bases", 
            len(tryfi.pets), 
            len(tryfi.bases)
        )
    except Exception as err:
        _LOGGER.error("Failed to initialize TryFi API: %s", err, exc_info=True)
        raise ConfigEntryNotReady from err
    
    # Verify successful login
    if not hasattr(tryfi, "currentUser") or tryfi.currentUser is None:
        raise ConfigEntryNotReady("Failed to authenticate with TryFi API")
    
    # Create the data update coordinator
    coordinator = TryFiDataUpdateCoordinator(
        hass,
        tryfi,
        polling_interval,
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator for platforms to access
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Add options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    # Register services
    await async_setup_services(hass)
    
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for TryFi."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # Remove coordinator
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok



async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    # Always allow removal of devices with "Base Station" in the name
    # These are the duplicate devices created with the wrong naming
    if device_entry.name and "Base Station" in device_entry.name:
        _LOGGER.info("Allowing removal of duplicate base station device: %s", device_entry.name)
        return True
    
    # Allow removal of devices with model "TryFi Base" (old format)
    if device_entry.model == "TryFi Base":
        _LOGGER.info("Allowing removal of old format base device: %s", device_entry.name)
        return True
    
    # Get the coordinator
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        
        # Get all current pet and base IDs from the API
        current_pet_ids = {pet.petId for pet in coordinator.data.pets}
        current_base_ids = {base.baseId for base in coordinator.data.bases}
        
        # Check if this device is still in the API
        for identifier in device_entry.identifiers:
            if identifier[0] == DOMAIN:
                device_id = identifier[1]
                # Remove "base_" prefix if present (old format)
                if device_id.startswith("base_"):
                    _LOGGER.info("Allowing removal of old format base device with base_ prefix: %s", device_id)
                    return True
                # If the device is no longer in the API, allow removal
                if device_id not in current_pet_ids and device_id not in current_base_ids:
                    _LOGGER.info("Allowing removal of device not in API: %s", device_id)
                    return True
    except Exception as e:
        _LOGGER.error("Error checking device removal: %s", e)
        # If there's an error, allow removal to help with cleanup
        return True
    
    # Don't allow removal of active devices
    _LOGGER.info("Device %s is still active in the API, removal not allowed", device_entry.name)
    return False


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up TryFi services."""
    
    async def handle_set_led_color(call: ServiceCall) -> None:
        """Handle set LED color service."""
        color_map = {
            "red": 1,
            "green": 2,
            "blue": 3,
            "yellow": 4,
            "magenta": 5,
            "cyan": 6,
            "orange": 7,
            "white": 8,
        }
        
        color = call.data.get("color", "white").lower()
        color_code = color_map.get(color, 8)
        
        # Get the pet from the target entity
        entity_id = call.data.get("entity_id")
        if not entity_id:
            raise HomeAssistantError("No entity_id provided")
            
        # Find the coordinator and pet
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, TryFiDataUpdateCoordinator):
                # Extract pet ID from entity_id (format: light.pet_name_collar_light)
                for pet in coordinator.data.pets:
                    if entity_id == f"light.{pet.name.lower().replace(' ', '_')}_collar_light":
                        await hass.async_add_executor_job(
                            pet.setLedColorCode,
                            coordinator.data.session,
                            color_code
                        )
                        await coordinator.async_request_refresh()
                        return
        
        raise HomeAssistantError(f"Pet not found for entity {entity_id}")
    
    async def handle_turn_on_led(call: ServiceCall) -> None:
        """Handle turn on LED service."""
        entity_id = call.data.get("entity_id")
        if not entity_id:
            raise HomeAssistantError("No entity_id provided")
            
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, TryFiDataUpdateCoordinator):
                for pet in coordinator.data.pets:
                    if entity_id == f"light.{pet.name.lower().replace(' ', '_')}_collar_light":
                        await hass.async_add_executor_job(
                            pet.turnOnOffLed,
                            coordinator.data.session,
                            True
                        )
                        await coordinator.async_request_refresh()
                        return
        
        raise HomeAssistantError(f"Pet not found for entity {entity_id}")
    
    async def handle_turn_off_led(call: ServiceCall) -> None:
        """Handle turn off LED service."""
        entity_id = call.data.get("entity_id")
        if not entity_id:
            raise HomeAssistantError("No entity_id provided")
            
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, TryFiDataUpdateCoordinator):
                for pet in coordinator.data.pets:
                    if entity_id == f"light.{pet.name.lower().replace(' ', '_')}_collar_light":
                        await hass.async_add_executor_job(
                            pet.turnOnOffLed,
                            coordinator.data.session,
                            False
                        )
                        await coordinator.async_request_refresh()
                        return
        
        raise HomeAssistantError(f"Pet not found for entity {entity_id}")
    
    async def handle_set_lost_mode(call: ServiceCall) -> None:
        """Handle set lost mode service."""
        mode = call.data.get("mode", "Safe")
        is_lost = mode == "Lost"
        
        entity_id = call.data.get("entity_id")
        if not entity_id:
            raise HomeAssistantError("No entity_id provided")
            
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, TryFiDataUpdateCoordinator):
                for pet in coordinator.data.pets:
                    if entity_id == f"select.{pet.name.lower().replace(' ', '_')}_lost_mode":
                        await hass.async_add_executor_job(
                            pet.setLostDogMode,
                            coordinator.data.session,
                            is_lost
                        )
                        await coordinator.async_request_refresh()
                        return
        
        raise HomeAssistantError(f"Pet not found for entity {entity_id}")
    
    # Register services
    hass.services.async_register(DOMAIN, "set_led_color", handle_set_led_color)
    hass.services.async_register(DOMAIN, "turn_on_led", handle_turn_on_led)
    hass.services.async_register(DOMAIN, "turn_off_led", handle_turn_off_led)
    hass.services.async_register(DOMAIN, "set_lost_mode", handle_set_lost_mode)