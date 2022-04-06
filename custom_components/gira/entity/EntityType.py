from enum import Enum


class EntityType(Enum):
    UNKNOWN = None
    LIGHT = 1
    DIMMABLE_LIGHT = 2
    OUTLET = 3
    BLIND = 4
    GARAGE = 5
    THERMOSTAT = 6
    BASIC_SENSOR = 7