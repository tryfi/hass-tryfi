"""Support for TryFi number entities."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass
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
    """Set up TryFi number entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        TryFiPetWeightNumber(coordinator, pet)
        for pet in coordinator.data.pets
    ]
    
    async_add_entities(entities)


class TryFiPetWeightNumber(CoordinatorEntity, NumberEntity):
    """Representation of a TryFi pet weight number entity."""
    
    _attr_has_entity_name = False
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 200
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = UnitOfMass.POUNDS
    
    def __init__(self, coordinator: Any, pet: Any) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-weight-setting"
        self._attr_name = f"{pet.name} Weight Setting"
        self._attr_icon = "mdi:weight"
    
    @property
    def pet(self) -> Any:
        """Get the pet object from coordinator data."""
        return self.coordinator.data.getPet(self._pet_id)
    
    @property
    def native_value(self) -> float | None:
        """Return the current weight value."""
        if self.pet:
            return getattr(self.pet, "weight", None)
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
    
    async def async_set_native_value(self, value: float) -> None:
        """Update the weight value."""
        # Note: The API doesn't appear to have a method to update weight
        # This would need to be implemented if the API supports it
        _LOGGER.warning(
            "Weight update not implemented - API method needed for pet %s",
            self.pet.name if self.pet else "unknown"
        )