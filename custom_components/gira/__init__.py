"""Gira Homeserver Integration"""

import gira_homeserver_api
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import time
from homeassistant.const import EVENT_HOMEASSISTANT_STOP


from .const import DOMAIN
from .PlatformManager import PlatformManager
from .EntityTranslater import EntityTranslator
from .ConfigurationEnumeration import ConfigurationEnumeration


platformManager = PlatformManager.getInstance()
entityLookupTable = {}
client = None


def setup(hass, config):
    try:
        connect(hass, config[DOMAIN])
    except:
        pass

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, onHassStop)

    return True


async def async_setup_entry(hass, entry):
    connect(hass, entry.data)
    return True


def connect(hass, config):
    global client
    client = gira_homeserver_api.Client(
        config[ConfigurationEnumeration.HOST.value],
        int(config[ConfigurationEnumeration.PORT.value]),
        config[ConfigurationEnumeration.USERNAME.value],
        config[ConfigurationEnumeration.PASSWORD.value],
    )

    def onDeviceValueListener(_id, value):
        _id = str(_id)
        if _id in entityLookupTable:
            entity = entityLookupTable[_id]
            entity._value = value
            entity.async_write_ha_state()

    def onClientReadyListener(token):
        parser = gira_homeserver_api.Parser()
        devices = parser.parse(client.getDevices(), client)
        entities = EntityTranslator.translate_devices_to_entities(devices)
        hass.data[DOMAIN] = {"entities": entities}
        platformManager.load_platform_integrations(hass, config)
        fillLookupTable(entities)

    client.onDeviceValue(onDeviceValueListener)
    client.onClientReady(onClientReadyListener)
    client.connect(asynchronous=True, reconnect=True)


def onHassStop(_data):
    if client != None:
        client.close()


def fillLookupTable(entities):
    for platform in entities:
        for entity in entities[platform]:
            entityLookupTable[str(entity._id)] = entity