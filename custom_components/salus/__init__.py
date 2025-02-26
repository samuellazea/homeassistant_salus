"""Support for Salus iT600."""
import logging
import time
from asyncio import sleep

from homeassistant import config_entries, core
from homeassistant.helpers import device_registry as dr

from homeassistant.const import (
    CONF_HOST,
    CONF_TOKEN
)

from pyit600.exceptions import IT600AuthenticationError, IT600ConnectionError
from pyit600.gateway import IT600Gateway

from .config_flow import CONF_FLOW_TYPE, CONF_USER
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

GATEWAY_PLATFORMS = ["climate", "binary_sensor", "switch", "cover", "sensor"]

async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Salus iT600 component."""
    _LOGGER.debug("Initializing Salus iT600 component setup")
    return True

async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up components from a config entry."""
    _LOGGER.debug("Setting up config entry: %s", entry.entry_id)
    hass.data[DOMAIN] = {}
    if entry.data[CONF_FLOW_TYPE] == CONF_USER:
        if not await async_setup_gateway_entry(hass, entry):
            _LOGGER.error("Failed to set up gateway entry")
            return False
    _LOGGER.debug("Successfully set up config entry")
    return True

async def async_setup_gateway_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up the Gateway component from a config entry."""
    host = entry.data[CONF_HOST]
    euid = entry.data[CONF_TOKEN]
    _LOGGER.debug("Provided host: %s", host)
    _LOGGER.debug("Provided token (EUID): %s", euid)

    # Connect to gateway
    gateway = IT600Gateway(host=host, euid=euid)
    try:
        for remaining_attempts in reversed(range(3)):
            try:
                _LOGGER.debug("Attempting to connect to gateway, attempts left: %d", remaining_attempts + 1)
                await gateway.connect()
                await gateway.poll_status()
                _LOGGER.debug("Successfully connected to gateway")
                break
            except Exception as e:
                _LOGGER.warning("Connection attempt failed: %s", str(e))
                if remaining_attempts == 0:
                    raise e
                else:
                    await sleep(3)
    except IT600ConnectionError as ce:
        _LOGGER.error("Connection error: check if you have specified gateway's HOST correctly.")
        return False
    except IT600AuthenticationError as ae:
        _LOGGER.error("Authentication error: check if you have specified gateway's EUID correctly.")
        return False

    hass.data[DOMAIN][entry.entry_id] = gateway

    gateway_info = gateway.get_gateway_device()
    _LOGGER.debug("Retrieved gateway info: %s", gateway_info)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, gateway_info.unique_id)},
        identifiers={(DOMAIN, gateway_info.unique_id)},
        manufacturer=gateway_info.manufacturer,
        name=gateway_info.name,
        model=gateway_info.model,
        sw_version=gateway_info.sw_version,
    )
    _LOGGER.debug("Device registered with Home Assistant")

    await hass.config_entries.async_forward_entry_setups(entry, GATEWAY_PLATFORMS)
    _LOGGER.debug("Forwarded entry setups for platforms: %s", GATEWAY_PLATFORMS)

    return True

async def async_unload_entry(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading config entry: %s", config_entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, GATEWAY_PLATFORMS
    )

    if unload_ok:
        _LOGGER.debug("Successfully unloaded platforms, removing gateway data")
        hass.data[DOMAIN].pop(config_entry.entry_id)
    else:
        _LOGGER.error("Failed to unload some platforms")

    return unload_ok
