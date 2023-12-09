"""Config flows for the Eltako integration."""
# https://developers.home-assistant.io/docs/config_entries_config_flow_handler

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE
from homeassistant.data_entry_flow import FlowResult

from homeassistant.helpers.reload import async_integration_yaml_config
from . import gateway
from .config_helpers import async_get_gateway_config_serial_port, async_get_list_of_gateways
from .const import DOMAIN, ERROR_INVALID_GATEWAY_PATH, LOGGER, CONF_SERIAL_PATH
from .schema import CONFIG_SCHEMA


class EltakoFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Eltako config flows."""

    VERSION = 1
    MANUAL_PATH_VALUE = "Custom path"

    def __init__(self) -> None:
        """Initialize the Eltako config flow."""

    async def async_step_user(self, user_input=None):
        """Handle an Eltako config flow start."""
        serial_port_from_config = await async_get_gateway_config_serial_port(self.hass, CONFIG_SCHEMA, async_integration_yaml_config)
        if serial_port_from_config is not None:
            return self.create_eltako_entry({
                CONF_SERIAL_PATH: serial_port_from_config
                })

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return await self.async_step_detect()

    async def async_step_detect(self, user_input=None):
        """Propose a list of detected gateways."""
        errors = {}
        
        if user_input is not None:
            if user_input[CONF_SERIAL_PATH] == self.MANUAL_PATH_VALUE:
                return await self.async_step_manual(None)
                
            if await self.validate_eltako_conf(user_input):
                return self.create_eltako_entry(user_input)
            
            errors = {CONF_SERIAL_PATH: ERROR_INVALID_GATEWAY_PATH}

        serial_paths = await self.hass.async_add_executor_job(gateway.detect)
        
        if len(serial_paths) == 0:
            return await self.async_step_manual(user_input)

        # serial_paths.append(self.MANUAL_PATH_VALUE)
        
        g_list = await async_get_list_of_gateways(self.hass, CONFIG_SCHEMA)

        #TODO: filter out initialized gateways
        #TODO: check if gateway is already inserted!
        #TODO: filter out taken serial paths'

        return self.async_show_form(
            step_id="Select USB Port for Gateway",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE): vol.In(g_list.values()),
                vol.Required(CONF_SERIAL_PATH): vol.In(serial_paths),
                }),
            errors=errors,
        )

    async def async_step_manual(self, user_input=None):
        """Request manual USB gateway path."""
        default_value = None
        errors = {}
        
        if user_input is not None:
            if await self.validate_eltako_conf(user_input):
                return self.create_eltako_entry(user_input)
            
            default_value = user_input[CONF_SERIAL_PATH]
            errors = {CONF_SERIAL_PATH: ERROR_INVALID_GATEWAY_PATH}

        g_list = await async_get_list_of_gateways(self.hass, CONFIG_SCHEMA)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE): vol.In(g_list.values()),
                vol.Required(CONF_SERIAL_PATH, default=default_value): str
            }),
            errors=errors,
        )

    async def validate_eltako_conf(self, user_input) -> bool:
        """Return True if the user_input contains a valid gateway path."""
        serial_path: str = user_input[CONF_SERIAL_PATH]
        baud_rate: int = -1
        gateway_selection: str = user_input[CONF_DEVICE]

        LOGGER.debug("serial_path: %s", serial_path)
        LOGGER.debug("gateway_selection: %s", gateway_selection)
        for gdc in gateway.GatewayDeviceTypes:
            LOGGER.debug("gdc %s", gdc)
            if gdc in gateway_selection:
                baud_rate = gateway.baud_rate_device_type_mapping[gdc]
                break

        path_is_valid = await self.hass.async_add_executor_job(
            gateway.validate_path, serial_path, baud_rate
        )
        return path_is_valid

    def create_eltako_entry(self, user_input):
        """Create an entry for the provided configuration."""
        return self.async_create_entry(title="Eltako", data=user_input)
