"""Support for TryFi select entities."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)

LOST_MODE_OPTIONS = ["Safe", "Lost"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TryFi select entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        TryFiLostModeSelect(coordinator, pet)
        for pet in coordinator.data.pets
    ]
    
    async_add_entities(entities)


class TryFiLostModeSelect(CoordinatorEntity, SelectEntity):
    """Representation of a TryFi lost mode select entity."""
    
    _attr_has_entity_name = False
    _attr_options = LOST_MODE_OPTIONS
    
    def __init__(self, coordinator: Any, pet: Any) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-lost"
        self._attr_name = f"{pet.name} Lost Mode"
        self._attr_icon = "mdi:map-search"
    
    @property
    def pet(self) -> Any:
        """Get the pet object from coordinator data."""
        return self.coordinator.data.getPet(self._pet_id)
    
    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if self.pet:
            is_lost = getattr(self.pet, "isLost", False)
            return "Lost" if is_lost else "Safe"
        return None
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.pet is not None
    
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
    
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if not self.pet:
            _LOGGER.error("Cannot set lost mode - pet not found")
            return
        
        if option not in self._attr_options:
            _LOGGER.error("Invalid option selected: %s", option)
            return
        
        # Set lost mode based on selected option
        is_lost = option == "Lost"
        
        try:
            await self.hass.async_add_executor_job(
                self.pet.setLostDogMode,
                self.coordinator.data.session,
                is_lost
            )
        except Exception:
            _LOGGER.warning("Couldn't change dog lost mode", exc_info=True)
        
        # Request coordinator update
        await self.coordinator.async_request_refresh()
        
        _LOGGER.info(
            "Set %s to %s mode",
            self.pet.name,
            option
        )