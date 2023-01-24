from .PlatformEnumeration import PlatformEnumeration
from .const import DOMAIN

from homeassistant.helpers import entity_registry
import logging

logger = logging.getLogger(__name__)

class PlatformManager:

    instance = None

    @staticmethod
    def getInstance():
        if PlatformManager.instance == None:
            PlatformManager.instance = PlatformManager()
        return PlatformManager.instance

    def __init__(self):
        self.platforms = [
            PlatformEnumeration.LIGHT,
            PlatformEnumeration.SWITCH,
            PlatformEnumeration.COVER,
            PlatformEnumeration.SENSOR,
            PlatformEnumeration.CLIMATE
        ]

    def getPlatforms(self):
        return self.platforms

    def load_platform_integrations(self, hass, config):
        for platform in self.platforms:
            hass.helpers.discovery.load_platform(platform.value, DOMAIN, {}, config)

    async def unload_platform_integrations(self, hass, entry):
        entities = []

        if DOMAIN in hass.data and "entities" in hass.data[DOMAIN]:
            for platform in self.platforms:
                if platform in hass.data[DOMAIN]["entities"]:
                    for entity in hass.data[DOMAIN]["entities"][platform]:
                        _id = entity.entity_id
                        entity_registry.async_get(hass).async_remove(_id)
                        logger.debug(f"successfully unloaded entity {_id}")
                
                await hass.config_entries.async_unload_platforms(entry, [platform.value])

        hass.data[DOMAIN] = {}
        
        return True