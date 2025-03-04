"""Support for (temperature, not thermostat) sensors."""
from datetime import timedelta
import logging
import async_timeout

import voluptuous as vol
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA

from homeassistant.const import (
    CONF_HOST,
    CONF_TOKEN
)

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): cv.string,
    }
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Salus sensors from a config entry."""

    gateway = hass.data[DOMAIN][config_entry.entry_id]

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        _LOGGER.debug("Fetching sensor data from gateway")
        async with async_timeout.timeout(10):
            await gateway.poll_status()
            data = gateway.get_sensor_devices()
            _LOGGER.debug("Received sensor data: %s", data)
            return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="sensor",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=30),
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()
    _LOGGER.debug("Coordinator initialized with data: %s", coordinator.data)

    async_add_entities(SalusSensor(coordinator, idx, gateway) for idx
                       in coordinator.data)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    pass


class SalusSensor(Entity):
    """Representation of a sensor."""

    def __init__(self, coordinator, idx, gateway):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._idx = idx
        self._gateway = gateway
        _LOGGER.debug("Initializing sensor with ID: %s", idx)

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        _LOGGER.debug("Requesting async update for sensor ID: %s", self._idx)
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        _LOGGER.debug("Sensor ID %s added to Home Assistant", self._idx)
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    def available(self):
        """Return if entity is available."""
        available = self._coordinator.data.get(self._idx).available
        _LOGGER.debug("Sensor ID %s availability: %s", self._idx, available)
        return available

    @property
    def device_info(self):
        """Return the device info."""
        info = {
            "name": self._coordinator.data.get(self._idx).name,
            "identifiers": {("salus", self._coordinator.data.get(self._idx).unique_id)},
            "manufacturer": self._coordinator.data.get(self._idx).manufacturer,
            "model": self._coordinator.data.get(self._idx).model,
            "sw_version": self._coordinator.data.get(self._idx).sw_version
        }
        _LOGGER.debug("Device info for sensor ID %s: %s", self._idx, info)
        return info

    @property
    def unique_id(self):
        """Return the unique id."""
        uid = self._coordinator.data.get(self._idx).unique_id
        _LOGGER.debug("Unique ID for sensor ID %s: %s", self._idx, uid)
        return uid

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        name = self._coordinator.data.get(self._idx).name
        _LOGGER.debug("Name for sensor ID %s: %s", self._idx, name)
        return name

    @property
    def state(self):
        """Return the state of the sensor."""
        state = self._coordinator.data.get(self._idx).state
        _LOGGER.debug("State for sensor ID %s: %s", self._idx, state)
        return state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        unit = self._coordinator.data.get(self._idx).unit_of_measurement
        _LOGGER.debug("Unit of measurement for sensor ID %s: %s", self._idx, unit)
        return unit

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        device_class = self._coordinator.data.get(self._idx).device_class
        _LOGGER.debug("Device class for sensor ID %s: %s", self._idx, device_class)
        return device_class
