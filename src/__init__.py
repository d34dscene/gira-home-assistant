"""Gira Homeserver Integration"""

import gira_homeserver_api
import logging
from .GiraLightEntity import GiraLightEntity
from .GiraDimmableLightEntity import GiraDimmableLightEntity

import time


def setup(hass, config):

    config = config["gira"]

    client = gira_homeserver_api.Client(
        config["host"], int(config["port"]), config["username"], config["password"]
    )
    client.connect(asynchronous=True, reconnect=False)

    time.sleep(2)

    parser = gira_homeserver_api.Parser()
    devices = parser.parse(client.getDevices(), client)

    logger = logging.getLogger(__name__)
    logger.info("Connected to Homeserver")

    translated_devices = translate_devices(devices)
    logger.debug("Translated devices")

    hass.data["gira"] = {"translated_devices": translated_devices}

    load_platform_integrations(hass, config)

    return True


def load_platform_integrations(hass, config):
    hass.helpers.discovery.load_platform("light", "gira", {}, config)


def translate_devices(devices):
    translated_devices = []

    for device in devices:
        translated_device = None

        if device.getName().lower().find("leuchte") >= 0:
            if isinstance(device, gira_homeserver_api.BinaryDevice):
                translated_device = GiraLightEntity.create(device)

            if isinstance(device, gira_homeserver_api.NormalizedDevice):
                translated_device = GiraDimmableLightEntity.create(device)

        if translated_device != None:
            translated_devices.append(translated_device)

    return translated_devices