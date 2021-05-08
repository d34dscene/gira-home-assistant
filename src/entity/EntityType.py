from enum import Enum


class EntityType(Enum):
    UNKNOWN = None
    LIGHT = 1
    DIMMABLE_LIGHT = 2
    OUTLET = 3