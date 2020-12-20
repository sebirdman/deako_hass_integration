"""Binary sensor platform for integration_blueprint."""
from homeassistant.components.binary_sensor import BinarySensorEntity

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,SUPPORT_BRIGHTNESS,LightEntity)


from .deako import Deako
_LOGGER: logging.Logger = logging.getLogger(__package__)

mydevices = {}

def got_state_callback(connection, device, callback_param=None):
    _LOGGER.error("Got state!")
    uuid = device["uuid"]
    mydevices[uuid].async_write_ha_state()

def got_device_callback(connection, device, callback_param=None):
    uuid = device["uuid"]
    
    if uuid not in mydevices:
      _LOGGER.error("Adding Device! " + device["name"] + " " + uuid)
      mydevices[uuid] = IntegrationBlueprintBinarySensor(connection, uuid, device["name"])
      _LOGGER.error("Added device! " + device["name"] + " " + uuid)
    else:
      mydevices[uuid].async_write_ha_state()

    if callback_param is not None:
      callback_param([mydevices[uuid]])
    else:
      _LOGGER.error("callback for adding devices is none, cannot add devices")

async def async_setup_entry(hass, config, async_add_devices):
    """Configure the platform."""
    ip = config.data['ip']

    connection = Deako(ip, "Home Assistant",
              got_state_callback, got_device_callback, async_add_devices)
    connection.connect()

class IntegrationBlueprintBinarySensor(LightEntity):
    """integration_blueprint binary_sensor class."""

    def __init__(self, connection, uuid, name):    
        self.uuid = uuid
        self.light_name = name
        self.connection = connection

    @property
    def unique_id(self):
        """Return the ID of this Hue light."""
        return self.uuid

    @property
    def name(self):
        """Return the name of the Hue light."""
        return self.light_name

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        state = self.connection.get_state_for_device(self.uuid)
        return state["power"]

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        state = self.connection.get_state_for_device(self.uuid)
        if state["dim"] is None:
            return None
        return state["dim"] * 2.55

    @property
    def supported_features(self):
        """Flag supported features."""
        state = self.connection.get_state_for_device(self.uuid)
        if state["dim"] is None:
          return 0
        return SUPPORT_BRIGHTNESS

    async def async_turn_on(self, **kwargs):
        state = self.connection.get_state_for_device(self.uuid)
        dim = 100
        if state["dim"] is not None:
          dim = state["dim"]
        if ATTR_BRIGHTNESS in kwargs:
          dim = (kwargs[ATTR_BRIGHTNESS] / 255) * 100
        self.connection.send_device_control(self.uuid, True, round(dim, 0))

    async def async_turn_off(self, **kwargs):
        state = self.connection.get_state_for_device(self.uuid)
        dim = 100
        if state["dim"] is not None:
          dim = state["dim"]
        if ATTR_BRIGHTNESS in kwargs:
          dim = (kwargs[ATTR_BRIGHTNESS] / 255) * 100
        self.connection.send_device_control(self.uuid, False, round(dim, 0))
