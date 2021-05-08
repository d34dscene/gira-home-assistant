from . import DOMAIN
from .PlatformEnumeration import PlatformEnumeration


def setup_platform(hass, config, add_entities, discovery_info=None):
    entities = hass.data[DOMAIN]["entities"][PlatformEnumeration.SWITCH]

    add_entities(entities)