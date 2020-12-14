"""Binary sensor platform for integration_blueprint."""
from homeassistant.components.binary_sensor import BinarySensorEntity

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,SUPPORT_BRIGHTNESS,LightEntity)


from .deako import Deako
_LOGGER: logging.Logger = logging.getLogger(__package__)

thisdict = {}
mydevices = {}

def got_state_callback(uuid, power, dim=None):
    _LOGGER.error("Got state!")
    thisdict[uuid]["power"] = power
    thisdict[uuid]["dim"] = dim
    mydevices[uuid].async_write_ha_state()

def got_device_callback(connection, name, uuid, power, dim=None, callback_param=None):
    _LOGGER.error("Got Device!")
    if name is None:
      return
    if uuid is None:
      return
    if uuid not in thisdict:
      thisdict[uuid] = {}
    thisdict[uuid]["power"] = power
    thisdict[uuid]["dim"] = dim
    
    if uuid not in mydevices:
      mydevices[uuid] = IntegrationBlueprintBinarySensor(connection, uuid, name)

    if callback_param is not None:
      callback_param([mydevices[uuid]])

async def async_setup_entry(hass, config, async_add_devices):
    """Configure the platform."""
    ip = config.data['ip']

    connection = Deako(ip, "Home Assistant",
              got_state_callback, got_device_callback, async_add_devices)
    connection.connect()
    connection.find_devices()

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
        return thisdict[self.uuid]["power"]

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        if thisdict[self.uuid]["dim"] is None:
            return None
        return thisdict[self.uuid]["dim"] * 2.55

    @property
    def supported_features(self):
        """Flag supported features."""
        if thisdict[self.uuid]["dim"] is None:
          return 0
        return SUPPORT_BRIGHTNESS


    async def async_turn_on(self, **kwargs):
        dim = 100
        if ATTR_BRIGHTNESS in kwargs:
          dim = (kwargs[ATTR_BRIGHTNESS] / 255) * 100
        self.connection.send_device_control(self.uuid, True, round(dim, 0))

    async def async_turn_off(self, **kwargs):
        dim = 100
        if ATTR_BRIGHTNESS in kwargs:
          dim = (kwargs[ATTR_BRIGHTNESS] / 255) * 100
        self.connection.send_device_control(self.uuid, False, round(dim, 0))
