"""Support for binary (door/window/smoke/leak) sensors."""
from datetime import timedelta
import logging
import async_timeout

import voluptuous as vol
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorEntity

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
    """Set up Salus binary sensors from a config entry."""
    _LOGGER.debug("Setting up entry for Salus binary sensors: %s", config_entry.entry_id)
    gateway = hass.data[DOMAIN][config_entry.entry_id]

    async def async_update_data():
        """Fetch data from API endpoint."""
        _LOGGER.debug("Fetching updated data from gateway")
        try:
            async with async_timeout.timeout(10):
                await gateway.poll_status()
                data = gateway.get_binary_sensor_devices()
                _LOGGER.debug("Fetched binary sensor data: %s", data)
                return data
        except Exception as e:
            _LOGGER.error("Error fetching sensor data: %s", e)
            raise UpdateFailed(f"Error fetching sensor data: {e}")

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

    async_add_entities(SalusBinarySensor(coordinator, idx, gateway) for idx in coordinator.data)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the binary_sensor platform."""
    _LOGGER.debug("async_setup_platform called, but not used.")
    pass


class SalusBinarySensor(BinarySensorEntity):
    """Representation of a binary sensor."""

    def __init__(self, coordinator, idx, gateway):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._idx = idx
        self._gateway = gateway
        _LOGGER.debug("Initialized SalusBinarySensor with index: %s", idx)

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        _LOGGER.debug("Requesting manual update for sensor: %s", self.unique_id)
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        _LOGGER.debug("Sensor added to Home Assistant: %s", self.unique_id)
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self):
        """Return if entity is available."""
        availability = self._coordinator.data.get(self._idx).available
        _LOGGER.debug("Sensor %s availability: %s", self.unique_id, availability)
        return availability

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
        _LOGGER.debug("Device info for sensor %s: %s", self.unique_id, info)
        return info

    @property
    def unique_id(self):
        """Return the unique id."""
        uid = self._coordinator.data.get(self._idx).unique_id
        _LOGGER.debug("Unique ID for sensor: %s", uid)
        return uid

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        name = self._coordinator.data.get(self._idx).name
        _LOGGER.debug("Sensor name: %s", name)
        return name

    @property
    def is_on(self):
        """Return the state of the sensor."""
        state = self._coordinator.data.get(self._idx).is_on
        _LOGGER.debug("Sensor %s state: %s", self.unique_id, state)
        return state

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        device_class = self._coordinator.data.get(self._idx).device_class
        _LOGGER.debug("Sensor %s device class: %s", self.unique_id, device_class)
        return device_class
