from enum import Enum


class PlatformEnumeration(str, Enum):
    UNKNOWN = "unknown"
    LIGHT = "light"
    SWITCH = "switch"
    COVER = "cover"
    SENSOR = "sensor"
    CLIMATE = "climate"