from .PlatformEnumeration import PlatformEnumeration
from .const import DOMAIN


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
        ]

    def getPlatforms(self):
        return self.platforms

    def load_platform_integrations(self, hass, config):
        for platform in self.platforms:
            hass.helpers.discovery.load_platform(platform, DOMAIN, {}, config)