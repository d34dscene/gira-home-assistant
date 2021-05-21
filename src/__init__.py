"""Gira Homeserver Integration"""

import gira_homeserver_api
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import time
import logging


from .const import DOMAIN
from .PlatformManager import PlatformManager
from .EntityTranslater import EntityTranslator
from .ConfigurationEnumeration import ConfigurationEnumeration


platformManager = PlatformManager.getInstance()
entityLookupTable = {}
LOGGER = logging.getLogger(__name__)


def onDeviceValueListener(_id, value):
    _id = str(_id)
    if _id in entityLookupTable:
        entity = entityLookupTable[_id]
        entity._value = value
        entity.async_write_ha_state()


def setup(hass, config):
    config = config[DOMAIN]

    client = gira_homeserver_api.Client(
        config[ConfigurationEnumeration.HOST.value],
        int(config[ConfigurationEnumeration.PORT.value]),
        config[ConfigurationEnumeration.USERNAME.value],
        config[ConfigurationEnumeration.PASSWORD.value],
    )

    client.onDeviceValue(onDeviceValueListener)
    client.connect(asynchronous=True, reconnect=False)

    time.sleep(2)

    parser = gira_homeserver_api.Parser()
    devices = parser.parse(client.getDevices(), client)
    entities = EntityTranslator.translate_devices_to_entities(devices)
    hass.data[DOMAIN] = {"entities": entities}
    platformManager.load_platform_integrations(hass, config)
    fillLookupTable(entities)

    return True


def fillLookupTable(entities):
    for platform in entities:
        for entity in entities[platform]:
            entityLookupTable[str(entity._id)] = entity