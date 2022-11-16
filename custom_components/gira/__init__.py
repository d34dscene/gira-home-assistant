"""Gira Homeserver Integration"""

import gira_homeserver_api
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import os
import json
import logging
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

from .const import DOMAIN
from .PlatformManager import PlatformManager
from .EntityTranslater import EntityTranslator
from .ConfigurationEnumeration import ConfigurationEnumeration
from .entity.GiraBasicSensorEntity import GiraBasicSensorEntity
from .PlatformEnumeration import PlatformEnumeration
from .ClientSingleton import ClientSingleton


platformManager = PlatformManager.getInstance()
entityLookupTable = {}
logger = logging.getLogger(__name__)

def setup(hass, config):
    try:
        connect(hass, config[DOMAIN])
    except:
        pass

    def handle_set_device_value(call):
        device_type = call.data.get("device_type")
        device_id = call.data.get("device_id")
        value = call.data.get("value")

        ClientSingleton.getInstance().setDeviceValue(device_type, device_id, value)
        

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, onHassStop)
    hass.services.register(DOMAIN, "set_device_value", handle_set_device_value)

    return True


async def async_setup_entry(hass, entry):
    connect(hass, entry.data)
    return True

async def async_unload_entry(hass, entry):
    client = ClientSingleton.getInstance()

    if client != None:
        client.close()
        logger.debug("Closed connection")
        entityLookupTable = {}

        ok = await PlatformManager.getInstance().unload_platform_integrations(hass, entry)

        if ok == False:
            return False
    else:
        logger.debug("Client is not setup")
    
    return True

def connect(hass, config):
    client = ClientSingleton.create(
        config[ConfigurationEnumeration.HOST.value],
        int(config[ConfigurationEnumeration.PORT.value]),
        config[ConfigurationEnumeration.USERNAME.value],
        config[ConfigurationEnumeration.PASSWORD.value],
    )

    def onDeviceValueListener(_id, value):
        if client.state == 2:
            _id = str(_id)
            if _id in entityLookupTable:
                entity = entityLookupTable[_id]
                entity._value = value
                
                try:
                    entity.async_write_ha_state()
                    logger.debug(f"changed value of entity {entity.name} ({_id}) to {value}")
                except Exception as exception:
                    logger.warning(f"failed to change entity value: {exception}")

    def onClientReadyListener(token):
        parser = gira_homeserver_api.Parser()
        devices = parser.parse(client.getDevices(), client)
        entities = EntityTranslator.translate_devices_to_entities(devices)

        logger.debug("Connection established")

        try:
            with open(os.path.abspath(os.path.dirname(__file__) + "/../gira-custom-sensors.json")) as f:
                sensors = json.loads(f.read())

                if isinstance(sensors, list):
                    for sensor in sensors:
                        if isinstance(sensor, dict) and "id" in sensor and "name" in sensor:
                            entity = GiraBasicSensorEntity.create(sensor, ClientSingleton.getInstance())
                            entities[PlatformEnumeration.SENSOR].append(entity)
        except IOError:
            logger.debug("'gira-custom-sensors.json' file not accessible")

        hass.data[DOMAIN] = {"entities": entities}
        platformManager.load_platform_integrations(hass, config)
        fillLookupTable(entities)

    def onConnectionErrorListener():
        logger.warning("Connection error")

    client.onDeviceValue(onDeviceValueListener)
    client.onClientReady(onClientReadyListener)
    client.onConnectionError(onConnectionErrorListener)
    client.connect(asynchronous=True, reconnect=False)


def onHassStop(_data):
    client = ClientSingleton.getInstance()

    if client != None:
        client.close()


def fillLookupTable(entities):
    for platform in entities:
        for entity in entities[platform]:
            entityLookupTable[str(entity._id)] = entity