"""Support for TryFi switch entities."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TryFi switch entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = []
    
    # Add pet switches
    for pet in coordinator.data.pets:
        if hasattr(pet, "device") and pet.device:
            entities.append(TryFiLostModeSwitch(coordinator, pet))
    
    async_add_entities(entities)


class TryFiLostModeSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a TryFi lost mode switch."""
    
    _attr_has_entity_name = False
    
    def __init__(self, coordinator: Any, pet: Any) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-lost-mode-switch"
        self._attr_name = f"{pet.name} Lost Mode Switch"
        self._attr_icon = "mdi:map-search"
    
    @property
    def pet(self) -> Any:
        """Get the pet object from coordinator data."""
        return self.coordinator.data.getPet(self._pet_id)
    
    @property
    def is_on(self) -> bool | None:
        """Return true if lost mode is on."""
        if self.pet:
            return bool(getattr(self.pet, "isLost", False))
        return None
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.pet is not None and hasattr(self.pet, "device") and self.pet.device is not None
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.pet
        if not pet:
            return {}
        
        device_info = {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
        
        # Add breed if available
        if hasattr(pet, "breed") and pet.breed:
            device_info["model"] = f"{MODEL} - {pet.breed}"
        
        # Add firmware version if available
        if hasattr(pet, "device") and pet.device:
            if hasattr(pet.device, "buildId"):
                device_info["sw_version"] = pet.device.buildId
        
        return device_info
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on lost mode."""
        if not self.pet:
            _LOGGER.error("Cannot turn on lost mode - pet not found")
            return
        
        await self.hass.async_add_executor_job(
            self.pet.setLostDogMode,
            self.coordinator.data.session,
            True
        )
        
        # Request coordinator update
        await self.coordinator.async_request_refresh()
        
        _LOGGER.info("Activated lost mode for %s", self.pet.name)
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off lost mode."""
        if not self.pet:
            _LOGGER.error("Cannot turn off lost mode - pet not found")
            return
        
        await self.hass.async_add_executor_job(
            self.pet.setLostDogMode,
            self.coordinator.data.session,
            False
        )
        
        # Request coordinator update
        await self.coordinator.async_request_refresh()
        
        _LOGGER.info("Deactivated lost mode for %s", self.pet.name)