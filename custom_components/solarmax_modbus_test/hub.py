
import asyncio
import logging
import time
from typing import Any
from datetime import timedelta, datetime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.util import dt as dt_util
from pymodbus.client import AsyncModbusTcpClient
from random import randint
from icmplib import NameLookupError, async_ping
from .const import DOMAIN
from . import const as _const

_LOGGER = logging.getLogger(__name__)

# Reduce pymodbus verbosity
logging.getLogger("pymodbus").setLevel(logging.WARNING)

class SolarMaxModbusHub(DataUpdateCoordinator[dict[str, Any]]):
    """SolarMax Modbus hub."""
    def __init__(self, hass: HomeAssistant, name: str, host: str, port: int, scan_interval: int, ping_host: str | None, check_status_first: bool = True) -> None:
        """Initialize the SolarMax Modbus hub."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=scan_interval),
            update_method=self._async_update_data,
        )
        self._host = host
        self._port = port
        self._scan_interval = scan_interval
        self._ping_host = ping_host
        self._check_status_first = check_status_first
        self._ping_host_reachable = False
        self.inverter_data: dict[str, Any] = {}
        self._key_dict = {}
        self._client: AsyncModbusTcpClient # to get rid of the pylance errors
        self._client = None # type: ignore
        self._icmp_privileged = hass.data[DOMAIN]["icmp_privileged"]

    async def start_coordinator(self) -> None:
        """Ensure the coordinators are running and scheduled."""
        _LOGGER.info("Starting main coordinator scheduling... ")
        try:
            await self.async_request_refresh()
            _LOGGER.info("Main coordinator refresh requested")
        except Exception as e:
            _LOGGER.error(f"Failed to request main coordinator refresh: {e}")

    async def _async_host_alive(self, host) -> bool:
        """Ping host to check if alive."""
        _LOGGER.debug("ping address: %s", self._ping_host)
        try:
            data = await async_ping(
                host,
                count=1,
                timeout=1,
                privileged=self._icmp_privileged,
            )
        except NameLookupError as error:
            _LOGGER.info("Error resolving host: %s", self._ping_host)
            self._ping_host_reachable = False
            raise error from None
        return data.is_alive

    async def _async_maintain_connection(self):
        """Maintain the connection."""
        if self._client is None:
            self._client = AsyncModbusTcpClient(host=self._host, port=self._port, timeout=3, retries=1)
        if not self._client.connected:
            _LOGGER.info(f"Connecting to Modbus client at {self._host}:{self._port}...")
            try:
                await self._client.connect()
            except Exception as e:
                _LOGGER.warning(f"connection error {e}")
            if not self._client.connected:
                _LOGGER.error(f"Failed to connect to Modbus client at {self._host}:{self._port}")
                raise ConnectionError(f"Failed to connect to {self._host}:{self._port}")
            _LOGGER.info(f"Connected to Modbus client at {self._host}:{self._port}")

    async def _async_update_data(self) -> dict[str, Any]:
        """Regular poll cycle: read fresh values."""
        _LOGGER.debug("Regular poll cycle")
        
        # Optional: Check gateway reachability via ping
        if self._ping_host != "":
            _LOGGER.debug("ping address: %s", self._ping_host)
            try:
                self._ping_host_reachable = await self._async_host_alive(
                    self._ping_host
                )
            except NameLookupError:
                _LOGGER.info("Error resolving host: %s", self._ping_host)
                self._ping_host_reachable = False
                return {"InverterMode": "Resolve Error"}
            if not self._ping_host_reachable:
                _LOGGER.debug("Gateway not reachable via ping")
                return {"InverterMode": "offline"}
        
        await self._async_maintain_connection()
        
        # Optional: First check only the status register to skip inactive inverters
        if self._check_status_first:
            try:
                status_reg = await self._client.read_holding_registers(4097, count=1)
                if status_reg.isError():
                    _LOGGER.warning("Could not read inverter status register")
                    return {"InverterMode": "Error"}
                
                # Decode status register (offset 0 = InverterMode)
                status_value = self._client.convert_from_registers(
                    status_reg.registers[0:1], 
                    self._client.DATATYPE.UINT16
                )
                
                if status_value in _const.STATUS_INVERTER_MODE:
                    inverter_mode = _const.STATUS_INVERTER_MODE[status_value]
                else:
                    inverter_mode = f"unknown {status_value}"
                
                self.inverter_data["InverterMode"] = inverter_mode
                _LOGGER.debug(f"Inverter status: {inverter_mode}")
                
                # Check if inverter is in an active state
                # Only read all registers if inverter is online (OnGrid, Standby, or Initial Mode)
                if inverter_mode not in ["OnGrid", "Standby", "Initial Mode"]:
                    _LOGGER.debug(f"Inverter in state '{inverter_mode}' - skipping full register read")
                    return {"InverterMode": inverter_mode}
                
            except Exception as e:
                _LOGGER.debug(f"Cannot read status register (inverter likely offline): {e}")
                return {"InverterMode": "offline"}
        
        # Read all 60 registers (either status check passed or disabled)
        try:
            regs = await self._client.read_holding_registers(4097, count=60)
            if regs.isError():
                _LOGGER.error("Error reading full register range")
                return {"InverterMode": inverter_mode}  # Return at least the status
        except Exception as e:
            _LOGGER.error(f"Error reading holding registers: {e}")
            return {"InverterMode": inverter_mode}
        
        _LOGGER.debug(f"Read {len(regs.registers)} registers from active inverter")
        
        # Process all registers
        for offset in range(len(regs.registers)):
            if offset in self._key_dict:
                key = self._key_dict[offset]["key"]
                data_type: str = self._key_dict[offset]["type"]
                if data_type.startswith("STATUS"):
                    q = self._client.convert_from_registers(regs.registers[offset:offset+1], self._client.DATATYPE.UINT16)
                    t = getattr(_const, data_type)
                    if t and q in t:
                        self.inverter_data[key] = t[q]
                    else:
                        self.inverter_data[key] = f"unknown {q}"
                else:
                    factor = self._key_dict[offset]["factor"]
                    t = getattr(self._client.DATATYPE, data_type)
                    data_len = t.value[1]
                    r = self._client.convert_from_registers(regs.registers[offset:offset + data_len], t)
                    self.inverter_data[key] = r * factor
        return self.inverter_data

    async def update_runtime_settings(self, scan_interval: int, ping_host:str | None, check_status_first: bool = True) -> None:
        """Update settings."""
        _LOGGER.info("Update settings")
        self._scan_interval = scan_interval
        self._ping_host = ping_host
        self._check_status_first = check_status_first

    async def reconfigure_connection_settings(self, host: str, port: int, scan_interval: int, ping_host:str | None, check_status_first: bool = True) -> None:
        """Update settings."""
        _LOGGER.info("Update settings")
        self._host = host
        self._port = port
        self._scan_interval = scan_interval
        self._ping_host = ping_host
        self._check_status_first = check_status_first

    def set_key_dict(self, key_dict):
        """Set mapping between register position and variable."""
        self._key_dict = key_dict

    async def async_read_serial_number(self) -> tuple[str | None, str | None]:
        """Read inverter serial number and detect model.
        
        Returns:
            tuple: (serial_number, model) or (None, None) if reading fails
        """
        try:
            await self._async_maintain_connection()
            
            # Read serial number from registers 6672-6678 (7 registers)
            sn_data = await self._client.read_holding_registers(6672, count=7)

            if sn_data.isError():
                _LOGGER.warning("Could not read serial number from registers 6672-6678")
                return None, None

            # Decode serial number: registers contain 16-bit values that need ASCII conversion
            serial_parts = []
            for register_value in sn_data.registers:
                if register_value > 0:
                    # Extract high byte and low byte
                    high_byte = (register_value >> 8) & 0xFF
                    low_byte = register_value & 0xFF
                    
                    # Add valid ASCII characters
                    if 32 <= high_byte <= 126:  # Printable ASCII
                        serial_parts.append(chr(high_byte))
                    if 32 <= low_byte <= 126:
                        serial_parts.append(chr(low_byte))

            serial_number = ''.join(serial_parts).strip()
            
            if not serial_number:
                _LOGGER.info("Serial number is empty")
                return None, "SolarMax"
            
            _LOGGER.info(f"Read serial number: {serial_number}")
            
            # Detect model based on serial number
            if serial_number.startswith("2245-"):
                model = "SolarMax 6SMT"
            else:
                model = "SolarMax"
            
            return serial_number, model

        except Exception as e:
            _LOGGER.warning(f"Error reading serial number: {e}")
            return None, None


class SolarMaxHistoryCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for reading historical data from SolarMax inverter."""
    
    def __init__(self, hass: HomeAssistant, hub: SolarMaxModbusHub) -> None:
        """Initialize the history coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{hub.name}_history",
            update_interval=None,  # Use custom update logic for fixed time
        )
        self._hub = hub
        self._last_import_date = None
        self._imported_dates = set()  # Track which dates we've already imported
        # Import when inverter is online (check inverter status)
        # Will import when inverter mode changes from offline to online
        self._last_inverter_status = None
        self._scheduled_update = None
    
    async def async_start(self) -> None:
        """Start the coordinator with automatic updates."""
        # Do first update immediately if inverter is online
        inverter_mode = self._hub.inverter_data.get("InverterMode", "unknown")
        # Online states: OnGrid, Standby, Initial Mode
        online_states = ["OnGrid", "Standby", "Initial Mode"]
        if inverter_mode in online_states:
            _LOGGER.info(f"Inverter is online ({inverter_mode})")
            # First: Sync RTC to ensure correct timestamps
            try:
                await self._sync_inverter_rtc()
            except Exception as e:
                _LOGGER.error(f"Failed to sync inverter RTC: {e}")
            # Then: Import historical data with correct timestamps
            _LOGGER.info("Performing initial history import")
            await self.async_refresh()
        else:
            _LOGGER.info(f"Inverter is offline ({inverter_mode}), history import will run when inverter comes online")
        
        # Start monitoring inverter status
        self._start_status_monitoring()
    
    def _start_status_monitoring(self) -> None:
        """Monitor inverter status and import when it comes online."""
        async def check_status():
            """Check inverter status periodically."""
            while True:
                await asyncio.sleep(60)  # Check every minute
                
                current_status = self._hub.inverter_data.get("InverterMode", "unknown")
                
                # Offline/error states
                offline_states = ["offline", "Resolve Error", "Shutdown", "Error"]
                # Online states
                online_states = ["OnGrid", "Standby", "Initial Mode"]
                
                # If inverter just came online (was offline, now online)
                if (self._last_inverter_status in offline_states or self._last_inverter_status is None) and current_status in online_states:
                    _LOGGER.info(f"Inverter came online (status: {current_status})")
                    
                    # Sync inverter RTC (Real Time Clock) first
                    try:
                        await self._sync_inverter_rtc()
                    except Exception as e:
                        _LOGGER.error(f"Failed to sync inverter RTC: {e}")
                    
                    # Check if we already imported today
                    today = datetime.now().strftime('%Y-%m-%d')
                    if today not in self._imported_dates:
                        _LOGGER.info("Starting history import")
                        await self.async_refresh()
                
                self._last_inverter_status = current_status
        
        # Start monitoring task
        self.hass.async_create_task(check_status())
    
    async def _sync_inverter_rtc(self) -> None:
        """Synchronize inverter's Real Time Clock with system time."""
        _LOGGER.info("Synchronizing inverter RTC with system time")
        
        try:
            now = datetime.now()
            
            # Register 12288: Year
            await self._hub._client.write_register(12288, now.year, slave=1)
            _LOGGER.debug(f"Wrote year: {now.year}")
            
            # Register 12289: Month (high byte) + Day (low byte)
            month_day = (now.month * 256) + now.day
            await self._hub._client.write_register(12289, month_day, slave=1)
            _LOGGER.debug(f"Wrote month/day: {now.month}/{now.day}")
            
            # Register 12290: Hour (high byte) + Minute (low byte)
            hour_minute = (now.hour * 256) + now.minute
            await self._hub._client.write_register(12290, hour_minute, slave=1)
            _LOGGER.debug(f"Wrote hour/minute: {now.hour}:{now.minute}")
            
            # Register 12291: 45 (high byte) + Second (low byte)
            # Note: 45 seems to be a constant, keeping it as in original script
            second_value = (45 * 256) + now.second
            await self._hub._client.write_register(12291, second_value, slave=1)
            _LOGGER.debug(f"Wrote second: {now.second}")
            
            _LOGGER.info(f"Successfully synced inverter RTC to {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            _LOGGER.error(f"Error syncing inverter RTC: {e}")
            raise
        
    async def _async_update_data(self) -> dict[str, Any]:
        """Read historical data and import to HA statistics."""
        _LOGGER.info("Reading historical data from inverter")
        
        try:
            await self._hub._async_maintain_connection()
            
            # Read 30 days of historical data
            # Each day has 48 registers, but we only use every 2nd starting from index 1
            all_statistics = []
            metadata = {
                "has_mean": False,
                "has_sum": True,
                "name": "Solar Production History",
                "source": DOMAIN,
                "statistic_id": f"{DOMAIN}:solar_production",
                "unit_of_measurement": "kWh",
            }
            
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Determine which days need to be imported
            days_to_import = []
            
            # Check all 30 days available in the inverter
            for day_offset in range(30):
                date = today - timedelta(days=day_offset)
                date_str = date.strftime('%Y-%m-%d')
                
                # Import if: first run OR date not yet imported OR within last 2 days (always refresh recent data)
                if not self._imported_dates or date_str not in self._imported_dates or day_offset < 2:
                    days_to_import.append(day_offset)
            
            if not self._imported_dates:
                _LOGGER.info(f"First run: importing all {len(days_to_import)} days of historical data")
            else:
                _LOGGER.info(f"Daily update: importing {len(days_to_import)} days (including catch-up for missed days)")
            
            for day_offset in days_to_import:
                # Calculate register address for this day
                start_addr = 49152 + (day_offset * 48)
                
                try:
                    regs = await self._hub._client.read_holding_registers(start_addr, count=48)
                    if regs.isError():
                        _LOGGER.warning(f"Error reading historical data for day offset {day_offset}")
                        continue
                    
                    # First register (index 0) contains day of month (1-31)
                    day_of_month = regs.registers[0]
                    
                    # Calculate expected date: offset 0 = today, offset 1 = yesterday, etc.
                    date = today - timedelta(days=day_offset)
                    
                    # Verify against inverter's day number
                    if date.day != day_of_month:
                        _LOGGER.warning(
                            f"Date mismatch at offset {day_offset}: "
                            f"calculated {date.strftime('%Y-%m-%d')} (day {date.day}), "
                            f"inverter reports day {day_of_month}"
                        )
                        # Try to correct: maybe system time is off
                        # Keep the calculated date but log for investigation
                    
                    date_str = date.strftime('%Y-%m-%d')
                    
                    # Extract every 2nd register starting from index 1, divide by 100
                    hourly_values = [regs.registers[i] / 100.0 for i in range(1, 48, 2)]
                    
                    # Create statistics for each hour
                    for hour in range(24):
                        if hour < len(hourly_values):
                            timestamp = date + timedelta(hours=hour)
                            value = hourly_values[hour]
                            
                            all_statistics.append({
                                "start": timestamp,
                                "state": value,
                                "sum": value,
                            })
                    
                    # Mark this date as imported
                    self._imported_dates.add(date_str)
                    _LOGGER.debug(f"Processed day {date_str}: {sum(hourly_values):.2f} kWh")
                    
                except Exception as e:
                    _LOGGER.error(f"Error processing day offset {day_offset}: {e}")
                    continue
            
            # Import all statistics to Home Assistant
            if all_statistics:
                _LOGGER.info(f"Importing {len(all_statistics)} historical statistics to Home Assistant")
                async_import_statistics(self.hass, metadata, all_statistics)
                self._last_import_date = datetime.now()
                
            return {
                "statistics_imported": len(all_statistics),
                "last_import": self._last_import_date,
            }
            
        except Exception as e:
            _LOGGER.error(f"Failed to read historical data: {e}")
            raise
