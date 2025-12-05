"""Constants for the home-assistant-solar-max-modbus integration."""


from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfTime
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

ATTR_MANUFACTURER = "SolarMax"

DOMAIN = "solarmax_modbus_test"
DEFAULT_NAME = "SolarMax Test"
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_PORT = 502
CONF_SOLARMAX_HUB = "solarmax_hub"
DEFAULT_FAST_POLL = False

SENSOR_TYPES = {}

line_sensor = [
    {"name": "Voltage",   "type": "UINT16", "factor":  0.1,
     "unit": UnitOfElectricPotential.VOLT, "device_class": SensorDeviceClass.VOLTAGE,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:sine-wave"},
    {"name": "Current",   "type": "UINT16", "factor": 0.01,
     "unit": UnitOfElectricCurrent.AMPERE, "device_class": SensorDeviceClass.CURRENT,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:current-ac"},
    {"name": "Power",     "type": "UINT32", "factor":  0.1,
     "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:transmission-tower"},
    {"name": "Frequency", "type": "UINT16", "factor": 0.01,
     "unit": UnitOfFrequency.HERTZ, "device_class": SensorDeviceClass.FREQUENCY,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:sine-wave"},
]

pv_sensor = [
    {"name": "Voltage",   "type": "UINT16", "factor":  0.1,
     "unit": UnitOfElectricPotential.VOLT, "device_class": SensorDeviceClass.VOLTAGE,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:current-dc"},
    {"name": "Current",   "type": "UINT16", "factor": 0.01,
     "unit": UnitOfElectricCurrent.AMPERE, "device_class": SensorDeviceClass.CURRENT,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:current-dc"},
    {"name": "Power",     "type": "UINT32", "factor":  0.1,
     "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:solar-power"},
]

energy_sensor = [
    {"name": "Total Energy", "type": "UINT32", "factor":  1,
     "unit": UnitOfEnergy.KILO_WATT_HOUR, "device_class": SensorDeviceClass.ENERGY,
     "state_class": SensorStateClass.TOTAL_INCREASING, "icon": "mdi:solar-power"},
    {"name": "Total Hours", "type": "UINT32", "factor":  1,
     "unit": UnitOfTime.HOURS, "device_class": SensorDeviceClass.DURATION,
     "state_class": SensorStateClass.TOTAL_INCREASING, "icon": "mdi:timeline-clock-outline"},
    {"name": "Today Energy", "type": "UINT32", "factor":  1,
     "unit": UnitOfEnergy.KILO_WATT_HOUR, "device_class": SensorDeviceClass.ENERGY,
     "state_class": SensorStateClass.TOTAL, "icon": "mdi:solar-power"},
    {"name": "Today Energy2", "type": "UINT32", "factor":  0.001,
     "unit": UnitOfEnergy.KILO_WATT_HOUR, "device_class": SensorDeviceClass.ENERGY,
     "state_class": SensorStateClass.TOTAL, "icon": "mdi:solar-power"},
]

power_sensors = [
    {"name": "Active Power", "type": "UINT32", "factor":  0.1,
     "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:flash"},
    {"name": "Reactive Power", "type": "UINT32", "factor":  0.1,
     "unit": UnitOfReactivePower.VOLT_AMPERE_REACTIVE, "device_class": SensorDeviceClass.REACTIVE_POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:flash-outline"},
    {"name": "Today max Power", "type": "UINT32", "factor":  0.1,
     "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER,
     "state_class": SensorStateClass.MEASUREMENT, "icon": "mdi:solar-power"},
]

STATUS_INVERTER_MODE = {
  0: "Initial Mode",
  1: "Standby",
  3: "OnGrid",
  5: "Error",
  9: "Shutdown"
}

