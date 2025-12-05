"""Config flow for the home-assistant-solar-max-modbus integration."""

from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlowWithConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.network import is_host_valid
import homeassistant.helpers.config_validation as cv

from .const import DEFAULT_NAME, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN, DEFAULT_FAST_POLL

_LOGGER = logging.getLogger(__name__)

CONFIG_DATA_SCHEMA = vol.Schema(
    {
    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT):cv.port,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=5, msg="invalid_scan_interval")),
    vol.Optional("ping_host", default=""): str,
    vol.Optional("check_status_first", default=True): bool,
    }
)


async def validate_input(hass: HomeAssistant, user_data: dict[str, Any]): # -> dict[str, Any], dict[str, Any]:
    """Validate the user input is correct.

    Data has the keys from CONFIG_DATA_SCHEMA with values provided by the user.
    """
    errors = {}
    data = {}
    options = {}
    for conf_data_opt in CONFIG_DATA_SCHEMA.schema:
        name = f"{conf_data_opt}"
        if isinstance(conf_data_opt, vol.Optional):
            options[name] = user_data[name]
        else:
            data[name] = user_data[name]
    if not is_host_valid(user_data[CONF_HOST]):
        errors[CONF_HOST] = "invalid host"
    if user_data["ping_host"] != "" and not is_host_valid(user_data["ping_host"]):
        errors["ping_host"] = "invalid host"

    # Return info that you want to store in the config entry.
    return errors, data, options


class SolarMaxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for home-assistant-solar-max-modbus."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                errors, data, options = await validate_input(self.hass, user_input)
            except Exception as e:
                _LOGGER.exception(f"Unexpected exception {e}")
                errors["base"] = f"unknown error {e}"

            if not errors:
                await self.async_set_unique_id(user_input[CONF_HOST] + ":" + str(user_input[CONF_PORT]))
                self._abort_if_unique_id_configured(error="host/port already configured")
                return self.async_create_entry(title=user_input[CONF_NAME], data=data, options=options)

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}
        if user_input:
            try:
                errors, data, options = await validate_input(self.hass, user_input)
            except Exception as e:
                _LOGGER.exception(f"Unexpected exception {e}")
                errors["base"] = f"unknown error {e}"
            if not errors:
                await self.async_set_unique_id(user_input[CONF_HOST] + ":" + str(user_input[CONF_PORT]))
                _LOGGER.info(f"{user_input[CONF_HOST] + ":" + str(user_input[CONF_PORT])}")
                self._abort_if_unique_id_configured(error="host/port already configured")
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    title=user_input[CONF_NAME],
                    data_updates=data,
                    options=options
                )
        data_schema = self.add_suggested_values_to_schema(CONFIG_DATA_SCHEMA, self._get_reconfigure_entry().data)
        data_schema = self.add_suggested_values_to_schema(data_schema, self._get_reconfigure_entry().options)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow to allow configuration changes after setup."""
        return SolarMaxModbusOptionsFlowHandler(config_entry)


class SolarMaxModbusOptionsFlowHandler(OptionsFlowWithConfigEntry):
    """Handle an options flow for SolarMax Modbus."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            try:
                # Get the hub from the saved data with robust default handling
                hub = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get("hub")

                if hub is not None:
                    # Update the hub configuration only if hub exists
                    await hub.update_runtime_settings(
                        user_input[CONF_SCAN_INTERVAL],
                        user_input["ping_host"],
                        user_input.get("check_status_first", True)
                    )
                else:
                    # Hub not found - just log warning but continue to save options
                    _LOGGER.warning(f"Hub not found for entry_id: {self.config_entry.entry_id}. Options will be saved and hub will be created on reload.")

                # Save the new options in config_entry.options
                return self.async_create_entry(data=user_input)
            except Exception as e:
                _LOGGER.error(f"Error updating SolarMax Modbus configuration: {str(e)}")
                return self.async_abort(reason="update_failed")

        # Show only the the options form with defaults from config entry
        opts = {
            key: val for (key, val) in CONFIG_DATA_SCHEMA.schema.items() if isinstance(key, vol.Optional)
        }
        opt_data_schema = vol.Schema(opts)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(opt_data_schema, self.config_entry.options)
        )

