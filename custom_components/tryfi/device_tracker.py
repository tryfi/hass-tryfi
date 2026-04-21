"""Support for TryFi device tracking."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .pytryfi import PyTryFi, FiPet, FiBase, FiWifiNetwork
from . import TryFiDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TryFi device trackers from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    tryfi: PyTryFi = coordinator.data

    entities = []
    
    # Add pet trackers
    entities.extend([
        TryFiPetTracker(coordinator, pet)
        for pet in tryfi.pets
    ])
    
    # Add base station trackers
    entities.extend([
        TryFiBaseTracker(coordinator, base)
        for base in tryfi.bases
    ])

    # Add WiFi network trackers
    known_wifi_ssids: set[str] = set()
    for network in tryfi.wifiNetworks:
        known_wifi_ssids.add(network.ssid)
        entities.append(TryFiWifiNetworkTracker(coordinator, network))

    async_add_entities(entities, True)

    # Listen for new WiFi networks on coordinator updates
    def _check_new_wifi_networks() -> None:
        new_entities = []
        for network in coordinator.data.wifiNetworks:
            if network.ssid not in known_wifi_ssids:
                known_wifi_ssids.add(network.ssid)
                new_entities.append(TryFiWifiNetworkTracker(coordinator, network))
        if new_entities:
            async_add_entities(new_entities, True)

    config_entry.async_on_unload(coordinator.async_add_listener(_check_new_wifi_networks))


class TryFiPetTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a TryFi pet tracker."""
    
    _attr_has_entity_name = False
    
    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: FiPet) -> None:
        """Initialize the pet tracker."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-tracker"
        self._attr_name = f"{pet.name} Tracker"
    
    @property
    def pet(self) -> FiPet:
        """Get the pet object from coordinator data."""
        return self.coordinator.data.getPet(self._pet_id)
    
    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture."""
        if self.pet:
            return self.pet.photoLink
        return None
    
    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        if self.pet and hasattr(self.pet, "currLatitude"):
            return self.pet.currLatitude
        return None
    
    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        if self.pet and hasattr(self.pet, "currLongitude"):
            return self.pet.currLongitude
        return None
    
    @property
    def location_accuracy(self) -> float | None:
        """Returns accuracy in meters of the device."""
        if self.pet and self.pet.positionAccuracy is not None:
            return self.pet.positionAccuracy
        else:
            return 0

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.GPS
    
    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the device."""
        if self.pet and hasattr(self.pet, "device") and self.pet.device:
            return getattr(self.pet.device, "batteryPercent", None)
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
            "manufacturer": MANUFACTURER
        }
        
        # Add breed if available
        if hasattr(pet, "breed") and pet.breed:
            device_info["model"] = f"{MODEL} - {pet.breed}"
        else:
            device_info["model"] = MODEL
        
        # Add firmware version if available
        if hasattr(pet, "device") and pet.device:
            if hasattr(pet.device, "buildId") and pet.device.buildId is not None:
                device_info["sw_version"] = pet.device.buildId
        
        return device_info


class TryFiBaseTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a TryFi base station tracker."""
    
    _attr_has_entity_name = False
    
    def __init__(self, coordinator: Any, base: FiBase) -> None:
        """Initialize the base tracker."""
        super().__init__(coordinator)
        self._base_id = base.baseId
        self._attr_unique_id = f"{base.baseId}-tracker"
        self._attr_name = f"{base.name} Tracker"
        self._attr_icon = "mdi:home-map-marker"
    
    @property
    def base(self) -> FiBase:
        """Get the base object from coordinator data."""
        return self.coordinator.data.getBase(self._base_id)
    
    @property
    def latitude(self) -> float | None:
        """Return latitude value of the base station."""
        if self.base and self.base.latitude is not None:
            return float(self.base.latitude)
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the base station."""
        if self.base and self.base.longitude is not None:
            return float(self.base.longitude)
        return None
    
    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.GPS
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        base = self.base
        if not base:
            return {}
        
        return {
            "identifiers": {(DOMAIN, base.baseId)},
            "name": base.name,
            "manufacturer": MANUFACTURER,
            "model": "TryFi Base Station",
        }


class TryFiWifiNetworkTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a TryFi WiFi network tracker."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: Any, network: FiWifiNetwork) -> None:
        """Initialize the WiFi network tracker."""
        super().__init__(coordinator)
        self._ssid = network.ssid
        self._attr_unique_id = f"wifi-{network.ssid}-tracker"
        self._attr_icon = "mdi:wifi-marker"

    @property
    def network(self) -> FiWifiNetwork | None:
        """Get the WiFi network object from coordinator data."""
        return self.coordinator.data.getWifiNetwork(self._ssid)

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the WiFi network."""
        if self.network and self.network.latitude is not None:
            return float(self.network.latitude)
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the WiFi network."""
        if self.network and self.network.longitude is not None:
            return float(self.network.longitude)
        return None

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.GPS

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        network = self.network
        if not network:
            return {}

        return {
            "identifiers": {(DOMAIN, f"wifi-{network.ssid}")},
            "name": f"WiFi {network.ssid}",
            "manufacturer": MANUFACTURER,
            "model": "WiFi Network",
        }
