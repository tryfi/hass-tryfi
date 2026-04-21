"""Support for TryFi sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfTime,
    UnitOfMass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from custom_components.tryfi.pytryfi.fiPet import FiPet

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SENSOR_STATS_BY_TIME,
    SENSOR_STATS_BY_TYPE,
)
from .pytryfi import PyTryFi
from .pytryfi.fiWifiNetwork import FiWifiNetwork

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "battery": SensorEntityDescription(
        key="battery",
        name="Collar Battery Level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "steps": SensorEntityDescription(
        key="steps",
        name="Steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:paw",
    ),
    "goal": SensorEntityDescription(
        key="goal",
        name="Goal",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:paw",
    ),
    "distance": SensorEntityDescription(
        key="distance",
        name="Distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:map-marker-distance",
    ),
    "sleep": SensorEntityDescription(
        key="sleep",
        name="Sleep",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sleep",
    ),
    "nap": SensorEntityDescription(
        key="nap",
        name="Nap",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:power-sleep",
    ),
    "activity_type": SensorEntityDescription(
        key="activity_type",
        name="Activity Type",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:run",
    ),
    "current_place_name": SensorEntityDescription(
        key="current_place_name",
        name="Current Place Name",
        icon="mdi:map-marker",
    ),
    "current_place_address": SensorEntityDescription(
        key="current_place_address",
        name="Current Place Address",
        icon="mdi:home-map-marker",
    ),
    "connected_to": SensorEntityDescription(
        key="connected_to",
        name="Connected To",
        icon="mdi:wifi",
    ),
    "home_city_state": SensorEntityDescription(
        key="home_city_state",
        name="Home City State",
        icon="mdi:home-city",
    ),
    "gender": SensorEntityDescription(
        key="gender",
        name="Gender",
        icon="mdi:gender-male-female",
    ),
    "weight": SensorEntityDescription(
        key="weight",
        name="Weight",
        native_unit_of_measurement=UnitOfMass.POUNDS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weight",
    ),
    "age": SensorEntityDescription(
        key="age",
        name="Age",
        native_unit_of_measurement="years",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:calendar-clock",
    ),
    "connection_state": SensorEntityDescription(
        key="connection_state",
        name="Connection State",
        icon="mdi:connection",
    ),
    "led_color": SensorEntityDescription(
        key="led_color",
        name="LED Color",
        icon="mdi:palette",
    ),
    "module_id": SensorEntityDescription(
        key="module_id",
        name="Module ID",
        icon="mdi:identifier",
    ),
    "signal_strength": SensorEntityDescription(
        key="signal_strength",
        name="Signal Strength",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:signal",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TryFi sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    tryfi: PyTryFi = coordinator.data

    entities: list[SensorEntity] = []

    _LOGGER.info(
        "Setting up TryFi sensors - found %d pets and %d bases",
        len(tryfi.pets),
        len(tryfi.bases),
    )

    # Add pet sensors
    for pet in tryfi.pets:
        _LOGGER.debug("Adding sensors for pet: %s", pet.name)

        # Battery sensor
        entities.append(TryFiBatterySensor(coordinator, pet))

        # Activity stats sensors
        for stat_type in SENSOR_STATS_BY_TYPE:
            for stat_time in SENSOR_STATS_BY_TIME:
                entities.append(PetStatsSensor(coordinator, pet, stat_type, stat_time))

        # Generic sensors
        entities.extend(
            [
                PetGenericSensor(coordinator, pet, "activity_type"),
                PetGenericSensor(coordinator, pet, "current_place_name"),
                PetGenericSensor(coordinator, pet, "current_place_address"),
                PetGenericSensor(coordinator, pet, "connected_to"),
                PetGenericSensor(coordinator, pet, "home_city_state"),
                PetGenericSensor(coordinator, pet, "gender"),
                PetGenericSensor(coordinator, pet, "weight"),
                PetGenericSensor(coordinator, pet, "age"),
                PetGenericSensor(coordinator, pet, "connection_state"),
                PetGenericSensor(coordinator, pet, "led_color"),
                PetGenericSensor(coordinator, pet, "module_id"),
                PetGenericSensor(coordinator, pet, "signal_strength"),
            ]
        )

        # Add sleep quality score sensor
        if hasattr(pet, "device") and pet.device:
            entities.append(PetSleepQualitySensor(coordinator, pet))

            # Add behavior sensors for Series 3+ collars
            if pet.device.supportsAdvancedBehaviorStats():
                _LOGGER.debug("Adding behavior sensors for Series 3+ collar: %s", pet.name)
                for period in ["daily", "weekly", "monthly"]:
                    for behavior in ["barking", "licking", "scratching", "eating", "drinking"]:
                        entities.append(PetBehaviorSensor(coordinator, pet, behavior, "count", period))
                        entities.append(PetBehaviorSensor(coordinator, pet, behavior, "duration", period))
    
    # Add base sensors
    for base in tryfi.bases:
        _LOGGER.debug("Adding sensors for base: %s", base.name)
        entities.extend([
            TryFiBaseSensor(coordinator, base),
            TryFiBaseDiagnosticSensor(coordinator, base, "WiFi SSID"),
            TryFiBaseDiagnosticSensor(coordinator, base, "Base ID"),
            TryFiBaseDiagnosticSensor(coordinator, base, "Connection Quality"),
        ])

    # Add WiFi network sensors
    known_wifi_ssids: set[str] = set()
    for network in tryfi.wifiNetworks:
        _LOGGER.debug("Adding sensors for WiFi network: %s", network.ssid)
        known_wifi_ssids.add(network.ssid)
        entities.extend([
            TryFiWifiNetworkSensor(coordinator, network, "Status"),
            TryFiWifiNetworkSensor(coordinator, network, "Address"),
        ])

    async_add_entities(entities)

    # Listen for new WiFi networks on coordinator updates
    def _check_new_wifi_networks() -> None:
        new_entities = []
        for network in coordinator.data.wifiNetworks:
            if network.ssid not in known_wifi_ssids:
                known_wifi_ssids.add(network.ssid)
                new_entities.extend([
                    TryFiWifiNetworkSensor(coordinator, network, "Status"),
                    TryFiWifiNetworkSensor(coordinator, network, "Address"),
                ])
        if new_entities:
            async_add_entities(new_entities)

    config_entry.async_on_unload(coordinator.async_add_listener(_check_new_wifi_networks))


class TryFiSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for TryFi sensors."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: Any,
        entity_description: SensorEntityDescription | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        if entity_description:
            self.entity_description = entity_description


class TryFiBatterySensor(TryFiSensorBase):
    """Representation of a TryFi battery sensor."""

    def __init__(self, coordinator: Any, pet: Any) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, SENSOR_DESCRIPTIONS["battery"])
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-battery"
        self._attr_name = f"{pet.name} Collar Battery Level"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.coordinator.data.getPet(self._pet_id)
        return {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        # TODO: Can coordinator.data ever be None?
        if self.coordinator.data is None:
            return None
        pet = self.coordinator.data.getPet(self._pet_id)
        if pet and pet.device:
            return pet.device.batteryPercent
        return None

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        battery_level = self.native_value
        charging = False

        pet = self.coordinator.data.getPet(self._pet_id)
        if pet and pet.device:
            charging = pet.device.isCharging

        return icon_for_battery_level(battery_level, charging)


class PetStatsSensor(TryFiSensorBase):
    """Representation of a TryFi pet statistics sensor."""

    def __init__(
        self,
        coordinator: Any,
        pet: Any,
        stat_type: str,
        stat_time: str,
    ) -> None:
        """Initialize the statistics sensor."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._stat_type = stat_type.upper()
        self._stat_time = stat_time.upper()
        self._attr_unique_id = f"{pet.petId}-{stat_time.lower()}-{stat_type.lower()}"
        self._attr_name = f"{pet.name} {stat_time.title()} {stat_type.title()}"

        # Set attributes from description
        if stat_type.lower() in SENSOR_DESCRIPTIONS:
            description = SENSOR_DESCRIPTIONS[stat_type.lower()]
            self.entity_description = description

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.coordinator.data.getPet(self._pet_id)
        return {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        pet = self.coordinator.data.getPet(self._pet_id)
        if not pet:
            return None

        # Build the attribute name from stat_time and stat_type
        # e.g., "DAILY" + "STEPS" -> "dailySteps"
        attr_name = f"{self._stat_time.lower()}{self._stat_type.title()}"

        # Special case for total distance
        if self._stat_type == "DISTANCE":
            attr_name = f"{self._stat_time.lower()}TotalDistance"

        # Try to get the attribute value
        value = getattr(pet, attr_name, None)

        # Convert distance from meters to kilometers
        if value is not None and self._stat_type == "DISTANCE":
            value = round(value / 1000, 2)

        # Convert sleep/nap from seconds to minutes
        if value is not None and (
            self._stat_type == "SLEEP" or self._stat_type == "NAP"
        ):
            value = round(value / 60, 1)

        return value


class PetGenericSensor(TryFiSensorBase):
    """Representation of a generic TryFi pet sensor."""

    def __init__(self, coordinator: Any, pet: Any, key: str) -> None:
        """Initialize the generic sensor."""
        description = SENSOR_DESCRIPTIONS.get(key)
        super().__init__(coordinator, description)
        self._pet_id = pet.petId
        self._key = key
        sensor_type = description.name if description else key.replace("_", " ").title()
        self._attr_unique_id = f"{pet.petId}-{key.replace('_', '-').lower()}"
        self._attr_name = f"{pet.name} {sensor_type}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.coordinator.data.getPet(self._pet_id)
        return {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def options(self) -> list[str] | None:
        if self._key == "activity_type":
            return ["OngoingWalk", "OngoingRest"]
        else:
            return None

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        pet = self.coordinator.data.getPet(self._pet_id)
        if not pet:
            return None

        if self._key == "activity_type":
            return getattr(pet, "activityType", None)
        elif self._key == "current_place_name":
            return getattr(pet, "currPlaceName", None)
        elif self._key == "current_place_address":
            return getattr(pet, "currPlaceAddress", None)
        elif self._key == "connected_to":
            if hasattr(pet, "device") and pet.device:
                return getattr(pet.device, "connectedTo", None)
        elif self._key == "home_city_state":
            return getattr(pet, "homeCityState", None)
        elif self._key == "gender":
            return getattr(pet, "gender", None)
        elif self._key == "weight":
            return getattr(pet, "weight", None)
        elif self._key == "age":
            if hasattr(pet, "yearOfBirth") and pet.yearOfBirth:
                from datetime import datetime

                current_year = datetime.now().year
                age = current_year - pet.yearOfBirth
                return age
            return None
        elif self._key == "connection_state":
            if hasattr(pet, "device") and pet.device:
                return getattr(pet.device, "connectionStateType", None)
        elif self._key == "led_color":
            if hasattr(pet, "device") and pet.device:
                return getattr(pet.device, "ledColor", None)
        elif self._key == "module_id":
            if hasattr(pet, "device") and pet.device:
                return getattr(pet.device, "moduleId", None)
        elif self._key == "signal_strength":
            connected_to = getattr(pet.device, "connectedTo", None)
            if connected_to and connected_to == "ConnectedToCellular":
                return pet.device.connectionSignalStrength
            return None

        return None


class TryFiBaseSensor(TryFiSensorBase):
    """Representation of a TryFi base station sensor."""

    def __init__(self, coordinator: Any, base: Any) -> None:
        """Initialize the base sensor."""
        super().__init__(coordinator)
        self._base_id = base.baseId
        self._attr_unique_id = base.baseId
        self._attr_name = base.name
        self._attr_icon = "mdi:home-circle"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        base = self.coordinator.data.getBase(self._base_id)
        return {
            "identifiers": {(DOMAIN, base.baseId)},
            "name": base.name,
            "manufacturer": MANUFACTURER,
            "model": "TryFi Base Station",
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        base = self.coordinator.data.getBase(self._base_id)
        if not base:
            return None

        # Return detailed status including health
        if not base.online:
            return "Offline"
        elif hasattr(base, "onlineQuality") and base.onlineQuality == "UNHEALTHY":
            return "Unhealthy"
        else:
            return "Online"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional base station attributes."""
        base = self.coordinator.data.getBase(self._base_id)
        if not base:
            return {}

        attrs = {}

        # Network information
        if hasattr(base, "networkname") and base.networkname:
            attrs["wifi_network"] = base.networkname

        # Connection quality
        if hasattr(base, "onlineQuality"):
            attrs["connection_quality"] = base.onlineQuality

        # Last update time
        if hasattr(base, "lastUpdated"):
            attrs["last_updated"] = base.lastUpdated

        return attrs


class TryFiBaseDiagnosticSensor(TryFiSensorBase):
    """Representation of a TryFi base station diagnostic sensor."""

    def __init__(self, coordinator: Any, base: Any, sensor_type: str) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._base_id = base.baseId
        self._key = sensor_type
        self._attr_unique_id = f"{base.baseId}-{sensor_type.replace(' ', '-').lower()}"
        self._attr_name = f"{base.name} {sensor_type}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Get icon based on sensor type."""
        icons = {
            "WiFi SSID": "mdi:wifi",
            "Base ID": "mdi:identifier",
            "Connection Quality": "mdi:signal",
        }
        return icons.get(self._key, "mdi:information")

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        base = self.coordinator.data.getBase(self._base_id)
        return {
            "identifiers": {(DOMAIN, base.baseId)},
            "name": base.name,
            "manufacturer": MANUFACTURER,
            "model": "TryFi Base Station",
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        base = self.coordinator.data.getBase(self._base_id)
        if not base:
            return None

        if self._key == "WiFi SSID":
            return getattr(base, "networkname", None)
        elif self._key == "Base ID":
            return getattr(base, "baseId", None)
        elif self._key == "Connection Quality":
            return getattr(base, "onlineQuality", None)

        return None


class PetSleepQualitySensor(TryFiSensorBase):
    """Representation of a TryFi pet sleep quality sensor."""

    def __init__(self, coordinator: Any, pet: Any) -> None:
        """Initialize the sleep quality sensor."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-sleep-quality"
        self._attr_name = f"{pet.name} Sleep Quality Score"
        self._attr_icon = "mdi:sleep"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.coordinator.data.getPet(self._pet_id)
        return {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def native_value(self) -> StateType:
        """Calculate sleep quality score based on sleep patterns."""
        pet = self.coordinator.data.getPet(self._pet_id)
        if not pet:
            return None

        # Get daily sleep and nap in seconds from API
        daily_sleep_seconds = getattr(pet, "dailySleep", 0)
        daily_nap_seconds = getattr(pet, "dailyNap", 0)

        if daily_sleep_seconds is None:
            daily_sleep_seconds = 0
        if daily_nap_seconds is None:
            daily_nap_seconds = 0

        # Convert to minutes for calculation
        daily_sleep = daily_sleep_seconds / 60
        daily_nap = daily_nap_seconds / 60

        # Total rest in minutes
        total_rest = daily_sleep + daily_nap

        # Dogs typically need 12-14 hours of sleep per day (720-840 minutes)
        # Puppies and older dogs need more (up to 18-20 hours)
        optimal_rest = 780  # 13 hours as baseline

        if total_rest == 0:
            return 0

        # Calculate score based on how close to optimal
        if total_rest >= optimal_rest:
            # Good amount of rest
            score = min(100, 80 + (total_rest - optimal_rest) / 30)
        else:
            # Less than optimal
            score = max(0, (total_rest / optimal_rest) * 80)

        # Bonus points for good sleep/nap balance
        if daily_sleep > 0 and daily_nap > 0:
            balance_ratio = min(daily_sleep, daily_nap) / max(daily_sleep, daily_nap)
            score = min(100, score + (balance_ratio * 20))

        return round(score)


class PetBehaviorSensor(TryFiSensorBase):
    """Behavior tracking sensor for Series 3+ collars."""

    def __init__(
        self,
        coordinator: Any,
        pet: FiPet,
        behavior_type: str,
        metric_type: str,
        period: str = "daily",
    ) -> None:
        """Initialize the behavior sensor."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._behavior_type = behavior_type
        self._metric_type = metric_type
        self._period = period

        # Create unique ID and name
        self._attr_unique_id = (
            f"tryfi-pet-{pet.petId}-{period}-{behavior_type}-{metric_type}"
        )

        # Create human-readable name
        behavior_name = behavior_type.replace("_", " ").title()
        metric_name = "Count" if metric_type == "count" else "Duration"
        self._attr_name = f"{pet.name} {period.title()} {behavior_name} {metric_name}"

        # Set appropriate icon
        icon_map = {
            "barking": "mdi:dog",
            "licking": "mdi:water",
            "scratching": "mdi:paw",
            "eating": "mdi:food-drumstick",
            "drinking": "mdi:cup-water",
        }
        self._attr_icon = icon_map.get(behavior_type, "mdi:dog")

        # Set units and device class
        if metric_type == "count":
            self._attr_native_unit_of_measurement = "events"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:  # duration
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, pet.petId)},
            name=pet.name,
            manufacturer="TryFi",
            model="Series 3+ Collar",
        )

    def _fipet_attr_name(self) -> str:
        attr_name = f"{self._period}{self._behavior_type.title()}{'Count' if self._metric_type == 'count' else 'Duration'}"

        return attr_name

    @property
    def native_value(self) -> StateType:
        """Return the behavior metric value."""
        pet = self.coordinator.data.getPet(self._pet_id)
        if not pet:
            return None

        # Build attribute name
        attr_name = self._fipet_attr_name()

        # Get the value from the pet object
        value = getattr(pet, attr_name, None)

        # Return 0 if None
        return value if value is not None else 0


class TryFiWifiNetworkSensor(TryFiSensorBase):
    """Representation of a TryFi WiFi network sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Any, network: FiWifiNetwork, sensor_type: str) -> None:
        """Initialize the WiFi network sensor."""
        super().__init__(coordinator)
        self._ssid = network.ssid
        self._sensor_type = sensor_type
        self._attr_unique_id = f"wifi-{network.ssid}-{sensor_type.lower()}"
        self._attr_name = sensor_type
        self._attr_icon = "mdi:wifi-settings" if sensor_type == "Status" else "mdi:map-marker-outline"

    @property
    def network(self) -> FiWifiNetwork | None:
        """Get the WiFi network object from coordinator data."""
        return self.coordinator.data.getWifiNetwork(self._ssid)

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

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        network = self.network
        if not network:
            return None

        if self._sensor_type == "Status":
            return network.state
        elif self._sensor_type == "Address":
            return network.addressLabel

        return None


def icon_for_battery_level(
    battery_level: int | None, charging: bool = False
) -> str:
    """Return battery icon based on level and charging status."""
    if battery_level is None:
        return "mdi:battery-unknown"

    if charging:
        return "mdi:battery-charging"

    if battery_level >= 90:
        return "mdi:battery"
    elif battery_level >= 70:
        return "mdi:battery-80"
    elif battery_level >= 50:
        return "mdi:battery-60"
    elif battery_level >= 30:
        return "mdi:battery-40"
    elif battery_level >= 10:
        return "mdi:battery-20"
    else:
        return "mdi:battery-alert"
