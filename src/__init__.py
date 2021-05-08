"""Gira Homeserver Integration"""

import gira_homeserver_api

from .entity.EntityType import EntityType
from .entity.GiraLightEntity import GiraLightEntity
from .entity.GiraDimmableLightEntity import GiraDimmableLightEntity
from .entity.GiraOutletEntity import GiraOutletEntity
from .PlatformEnumeration import PlatformEnumeration

import enum
import logging
import time


platforms = [PlatformEnumeration.LIGHT, PlatformEnumeration.SWITCH]
DOMAIN = "gira"


def setup(hass, config):

    config = config[DOMAIN]

    client = gira_homeserver_api.Client(
        config["host"], int(config["port"]), config["username"], config["password"]
    )
    client.connect(asynchronous=True, reconnect=False)

    time.sleep(2)

    parser = gira_homeserver_api.Parser()
    devices = parser.parse(client.getDevices(), client)

    logger = logging.getLogger(__name__)
    logger.info("Connected to Homeserver")

    entities = translate_devices_to_entities(devices)
    logger.debug("Translated devices to entities")

    hass.data[DOMAIN] = {"entities": entities}

    load_platform_integrations(hass, config)

    return True


def load_platform_integrations(hass, config):
    for platform in platforms:
        hass.helpers.discovery.load_platform(platform, DOMAIN, {}, config)


def determineEntityType(device):
    searchName = device.getName().lower()
    if searchName.find("leuchte") >= 0:
        if isinstance(device, gira_homeserver_api.BinaryDevice):
            return EntityType.LIGHT, PlatformEnumeration.LIGHT
        elif isinstance(device, gira_homeserver_api.NormalizedDevice):
            return EntityType.DIMMABLE_LIGHT, PlatformEnumeration.LIGHT
    elif searchName.find("steckdose") >= 0:
        return EntityType.OUTLET, PlatformEnumeration.SWITCH

    return EntityType.UNKNOWN, PlatformEnumeration.UNKNOWN


def translate_devices_to_entities(devices):
    entities = {}

    for platform in platforms:
        entities[platform] = []

    for device in devices:
        entity = None
        entityType, platform = determineEntityType(device)

        if entityType == EntityType.LIGHT:
            entity = GiraLightEntity.create(device)
        elif entityType == EntityType.DIMMABLE_LIGHT:
            entity = GiraDimmableLightEntity.create(device)
        elif entityType == EntityType.OUTLET:
            entity = GiraOutletEntity.create(device)

        if platform != PlatformEnumeration.UNKNOWN and entityType != EntityType.UNKNOWN:
            entities[platform].append(entity)

    return entities