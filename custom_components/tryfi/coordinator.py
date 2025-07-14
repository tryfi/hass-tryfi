from datetime import timedelta
import logging
import homeassistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .pytryfi import PyTryFi

_LOGGER = logging.getLogger(__name__)

class TryFiDataUpdateCoordinator(DataUpdateCoordinator[PyTryFi]):
    """Class to manage fetching TryFi data from the API."""
    
    def __init__(
        self,
        hass: homeassistant,
        tryfi: PyTryFi,
        polling_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        self.tryfi = tryfi
        self._previous_states = {}
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
        )
    
    async def _async_update_data(self) -> PyTryFi:
        """Fetch data from TryFi API."""
        try:
            await self.hass.async_add_executor_job(self.tryfi.update)
            _LOGGER.info(
                "TryFi data updated: %d pets, %d bases", 
                len(self.tryfi.pets), 
                len(self.tryfi.bases)
            )
            
            # Check for state changes and fire events
            await self._check_state_changes()
            
        except Exception as err:
            raise UpdateFailed(f"Error communicating with TryFi API: {err}") from err
        
        return self.tryfi
    
    async def _check_state_changes(self) -> None:
        """Check for state changes and fire events."""
        for pet in self.tryfi.pets:
            pet_id = pet.petId
            prev_state = self._previous_states.get(pet_id, {})
            
            # Check location changes
            current_location = getattr(pet, "currPlaceName", None)
            prev_location = prev_state.get("location")
            if current_location != prev_location and prev_location is not None:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_pet_location_changed",
                    {
                        "pet_id": pet_id,
                        "pet_name": pet.name,
                        "old_location": prev_location,
                        "new_location": current_location,
                    }
                )
            
            # Check battery level
            if hasattr(pet, "device") and pet.device:
                current_battery = getattr(pet.device, "batteryPercent", None)
                prev_battery = prev_state.get("battery")
                
                # Fire event if battery drops below 20%
                if (current_battery is not None and prev_battery is not None and 
                    current_battery < 20 and prev_battery >= 20):
                    self.hass.bus.async_fire(
                        f"{DOMAIN}_low_battery",
                        {
                            "pet_id": pet_id,
                            "pet_name": pet.name,
                            "battery_level": current_battery,
                        }
                    )
                
                # Check lost mode changes
                current_lost = getattr(pet, "isLost", False)
                prev_lost = prev_state.get("is_lost", False)
                if current_lost != prev_lost:
                    self.hass.bus.async_fire(
                        f"{DOMAIN}_lost_mode_changed",
                        {
                            "pet_id": pet_id,
                            "pet_name": pet.name,
                            "is_lost": current_lost,
                        }
                    )
                
                # Check connection state
                current_connected = getattr(pet.device, "connectionStateType", None)
                prev_connected = prev_state.get("connection_state")
                if current_connected != prev_connected and prev_connected is not None:
                    self.hass.bus.async_fire(
                        f"{DOMAIN}_connection_state_changed",
                        {
                            "pet_id": pet_id,
                            "pet_name": pet.name,
                            "old_state": prev_connected,
                            "new_state": current_connected,
                            "is_connected": current_connected == "ConnectedToCellular" or current_connected == "ConnectedToBase",
                        }
                    )
                
                # Update previous state
                self._previous_states[pet_id] = {
                    "location": current_location,
                    "battery": current_battery,
                    "is_lost": current_lost,
                    "connection_state": current_connected,
                }
