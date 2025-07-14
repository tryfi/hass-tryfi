"""Support for TryFi collar LED lights."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.light import (
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import TryFiDataUpdateCoordinator

from .pytryfi import FiPet
from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color to RGB tuple.
    
    Args:
        hex_color: Hex color string (e.g., "#RRGGBB" or "RRGGBB")
        
    Returns:
        RGB tuple (red, green, blue)
    """
    # Remove the "#" if present
    hex_color = hex_color.lstrip('#')
    
    # Convert hex to RGB
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def calculate_distance(color1: tuple[int, int, int], color2: tuple[int, int, int]) -> float:
    """Calculate Euclidean distance between two RGB colors.
    
    Args:
        color1: First RGB color tuple
        color2: Second RGB color tuple
        
    Returns:
        Euclidean distance between the two colors
    """
    return math.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)))


def find_closest_color_code(
    target_color: tuple[int, int, int],
    color_map: dict[int, tuple[int, int, int]]
) -> int:
    """Find the color code closest to the target RGB color.
    
    Args:
        target_color: Target RGB color tuple
        color_map: Map of color codes to RGB tuples
        
    Returns:
        Color code closest to the target color
    """
    min_distance = float('inf')
    closest_color_code = 8  # Default to white
    
    for code, color in color_map.items():
        distance = calculate_distance(target_color, color)
        if distance < min_distance:
            min_distance = distance
            closest_color_code = code
    
    return closest_color_code


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TryFi lights from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        TryFiPetLight(coordinator, pet)
        for pet in coordinator.data.pets
        if hasattr(pet, "device") and pet.device
    ]
    
    async_add_entities(entities)


class TryFiPetLight(CoordinatorEntity, LightEntity):
    """Representation of a TryFi collar LED light."""
    
    _attr_has_entity_name = False
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    
    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: FiPet) -> None:
        """Initialize the light entity."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-light"
        self._attr_name = f"{pet.name} Collar Light"
        
        # Build color map from available LED colors
        self._color_map: dict[int, tuple[int, int, int]] = {}
        if hasattr(pet.device, "availableLedColors") and pet.device.availableLedColors is not None:
            for led_color in pet.device.availableLedColors:
                if hasattr(led_color, "ledColorCode") and hasattr(led_color, "hexCode"):
                    self._color_map[led_color.ledColorCode] = hex_to_rgb(led_color.hexCode)
        
        # Default color map if none available
        if not self._color_map:
            self._color_map = {
                1: (255, 0, 0),      # Red
                2: (0, 255, 0),      # Green
                3: (0, 0, 255),      # Blue
                4: (255, 255, 0),    # Yellow
                5: (255, 0, 255),    # Magenta
                6: (0, 255, 255),    # Cyan
                7: (255, 165, 0),    # Orange
                8: (255, 255, 255),  # White
            }
    
    @property
    def pet(self) -> Any:
        """Get the pet object from coordinator data."""
        return self.coordinator.data.getPet(self._pet_id)
    
    @property
    def is_on(self) -> bool | None:
        """Return true if the light is on."""
        if self.pet and hasattr(self.pet, "device") and self.pet.device:
            return bool(getattr(self.pet.device, "ledOn", False))
        return None
    
    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the RGB color value."""
        if self.pet and hasattr(self.pet, "device") and self.pet.device:
            hex_color = getattr(self.pet.device, "ledColorHex", None)
            if hex_color:
                try:
                    return hex_to_rgb(hex_color)
                except (ValueError, IndexError):
                    _LOGGER.debug("Invalid color hex: %s", hex_color)
        return None
    
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
        """Turn on the light."""
        if not self.pet:
            _LOGGER.error("Cannot turn on light - pet not found")
            return
        
        # Turn on the LED
        await self.hass.async_add_executor_job(
            self.pet.turnOnOffLed,
            self.coordinator.data.session,
            True
        )
        
        # Set color if requested
        if ATTR_RGB_COLOR in kwargs:
            requested_color = kwargs[ATTR_RGB_COLOR]
            closest_color_code = find_closest_color_code(requested_color, self._color_map)
            
            await self.hass.async_add_executor_job(
                self.pet.setLedColorCode,
                self.coordinator.data.session,
                closest_color_code
            )
        
        # Request coordinator update
        await self.coordinator.async_request_refresh()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        if not self.pet:
            _LOGGER.error("Cannot turn off light - pet not found")
            return
        
        await self.hass.async_add_executor_job(
            self.pet.turnOnOffLed,
            self.coordinator.data.session,
            False
        )
        
        # Request coordinator update
        await self.coordinator.async_request_refresh()