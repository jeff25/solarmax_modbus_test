
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, line_sensor, pv_sensor, energy_sensor, power_sensors
from .hub import SolarMaxModbusHub
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass
import logging
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription
from homeassistant.const import UnitOfPower, UnitOfTemperature


_LOGGER = logging.getLogger(__name__)

@dataclass
class SolarMaxSensorEntityDescription(SensorEntityDescription):
    """A class that describes SolarMax sensor entities."""
    factor: float = 1
    position: float = 0
    data_type: str = ""


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up SolarMax sensors from a config entry."""
    hub: SolarMaxModbusHub = hass.data[DOMAIN][entry.entry_id]["hub"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    entities = []
    offset = 0
    key_dict = {}
    for i in range(3):
        for sens in line_sensor:
        # {"name": "Voltage",   "type": "uint16", "factor":  0.1,
        #  "unit": UnitOfElectricPotential.VOLT, "device_class": SensorDeviceClass.VOLTAGE,
        #  "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:sine-wave"},
            sensor_key = f"L{i+1}{sens["name"]}"
            sensor = SolarMaxSensorEntityDescription(
                name=f"L{i+1} {sens["name"]}",
                key=sensor_key,
                native_unit_of_measurement=sens["unit"],
                icon=sens["icon"],
                device_class=sens["device_class"],
                state_class=SensorStateClass.MEASUREMENT,
                entity_registry_enabled_default=True,
                factor=sens["factor"],
                data_type=sens["type"]
            )
            entity = SolarMaxSensor(hub, device_info, sensor)
            entities.append(entity)
            key_dict[offset] = {"key": sensor_key, "type": sens["type"], "factor": sens["factor"]}
            offset += 1
            if str(sens["type"]).endswith("32"):
                offset += 1
            elif str(sens["type"]).endswith("64"):
                offset += 3
    for i in range(3):
        for sens in pv_sensor:
        # {"name": "Voltage",   "type": "uint16", "factor":  0.1,
        #  "unit": UnitOfElectricPotential.VOLT, "device_class": SensorDeviceClass.VOLTAGE,
        #  "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:sine-wave"},
            sensor_key = f"PV{i+1}{sens["name"]}"
            sensor = SolarMaxSensorEntityDescription(
                name=f"PV{i+1} {sens["name"]}",
                key=sensor_key,
                native_unit_of_measurement=sens["unit"],
                icon=sens["icon"],
                device_class=sens["device_class"],
                state_class=SensorStateClass.MEASUREMENT,
                entity_registry_enabled_default=True,
                factor=sens["factor"],
                data_type=sens["type"]
            )
            entity = SolarMaxSensor(hub, device_info, sensor)
            entities.append(entity)
            key_dict[offset] = {"key": sensor_key, "type": sens["type"], "factor": sens["factor"]}
            offset += 1
            if str(sens["type"]).endswith("32"):
                offset += 1
            elif str(sens["type"]).endswith("64"):
                offset += 3

    sensor_key = "Temperature"
    sensor = SolarMaxSensorEntityDescription(
        name="Temperature",
        key=sensor_key,
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=True,
        data_type="UINT16"
    )
    entity = SolarMaxSensor(hub, device_info, sensor)
    entities.append(entity)
    key_dict[offset] = {"key": sensor_key, "type": "UINT16", "factor": 1}
    offset += 1

    sensor_key = "InverterMode"
    sensor = SolarMaxSensorEntityDescription(
        name="Inverter Mode",
        key=sensor_key,
        icon="mdi:information-outline",
        entity_registry_enabled_default=True,
        data_type="STATUS_INVERTER_MODE"
    )
    entity = SolarMaxSensor(hub, device_info, sensor)
    entities.append(entity)
    key_dict[offset] = {"key": sensor_key, "type": "STATUS_INVERTER_MODE", "factor": 1}
    offset += 1

    offset += 3 # skip 3 byte

    for sens in energy_sensor:
    # {"name": "Voltage",   "type": "uint16", "factor":  0.1,
    #  "unit": UnitOfElectricPotential.VOLT, "device_class": SensorDeviceClass.VOLTAGE,
    #  "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:sine-wave"},
        sensor_key = sens["name"].replace(" ", "_")
        sensor = SolarMaxSensorEntityDescription(
            name=sens["name"],
            key=sensor_key,
            native_unit_of_measurement=sens["unit"],
            icon=sens["icon"],
            device_class=sens["device_class"],
            state_class=sens["state_class"],
            entity_registry_enabled_default=True,
            factor=sens["factor"],
            data_type=sens["type"]
        )
        entity = SolarMaxSensor(hub, device_info, sensor)
        entities.append(entity)
        key_dict[offset] = {"key": sensor_key, "type": sens["type"], "factor": sens["factor"]}
        offset += 1
        if str(sens["type"]).endswith("32"):
            offset += 1
        elif str(sens["type"]).endswith("64"):
            offset += 3

    offset += 14 # skip 14 regs

    for sens in power_sensors:
    # {"name": "Voltage",   "type": "uint16", "factor":  0.1,
    #  "unit": UnitOfElectricPotential.VOLT, "device_class": SensorDeviceClass.VOLTAGE,
    #  "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:sine-wave"},
        sensor_key = sens["name"].replace(" ", "_")
        sensor = SolarMaxSensorEntityDescription(
            name=sens["name"],
            key=sensor_key,
            native_unit_of_measurement=sens["unit"],
            icon=sens["icon"],
            device_class=sens["device_class"],
            state_class=sens["state_class"],
            entity_registry_enabled_default=True,
            factor=sens["factor"],
            data_type=sens["type"]
        )
        entity = SolarMaxSensor(hub, device_info, sensor)
        entities.append(entity)
        key_dict[offset] = {"key": sensor_key, "type": sens["type"], "factor": sens["factor"]}
        offset += 1
        if str(sens["type"]).endswith("32"):
            offset += 1
        elif str(sens["type"]).endswith("64"):
            offset += 3

    async_add_entities(entities)
    hub.set_key_dict(key_dict)
    _LOGGER.info(f"Added {len(entities)} SolarMax sensors")

class SolarMaxSensor(CoordinatorEntity, SensorEntity):
    """Representation of an SolarMax Modbus sensor."""

    def __init__(self, hub: SolarMaxModbusHub, device_info: dict, description: SolarMaxSensorEntityDescription):
        """Initialize the sensor."""
        super().__init__(coordinator=hub)
        self.entity_description = description
        self._attr_device_info = device_info
        # Stable unique_id: independent of coordinator name
        device_name = device_info.get("name", "SolarMax")
        self._attr_unique_id = f"{device_name}_{description.key}"
        # IMPORTANT: With has_entity_name=True NO device prefix in the name!
        # HA automatically shows "<Device Name> <Entity Name>".
        self._attr_name = description.name
        # Recommended Core Standard: Entities have their own names
        self._attr_has_entity_name = True
        self._attr_entity_registry_enabled_default = description.entity_registry_enabled_default
        self._attr_force_update = description.force_update

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Use coordinator.data which will fall back to inverter_data if None
        coordinator_data = self.coordinator.data
        if coordinator_data is None:
            if hasattr(self.coordinator, 'inverter_data'):
                coordinator_data = self.coordinator.inverter_data
            else:
                _LOGGER.debug(f"Coordinator data not yet available for sensor {self._attr_name}")
                return None

        value = coordinator_data.get(self.entity_description.key)
        if value is None:
            _LOGGER.debug(f"No data for sensor {self._attr_name}")
        return value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # _LOGGER.debug(f"Sensor {self._attr_name} added to Home Assistant")
