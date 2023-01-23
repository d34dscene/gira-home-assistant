from homeassistant.components.cover import (
    CoverEntity,
    DEVICE_CLASS_GARAGE,
    SUPPORT_OPEN,
    SUPPORT_CLOSE
)
from .GiraEntity import GiraEntity

STATE_OPEN = "open"
STATE_CLOSE = "close"

class GiraGarageDoorEntity(CoverEntity, GiraEntity):
    @staticmethod
    def create(open_device, close_device):
        return GiraGarageDoorEntity(open_device, close_device)

    def __init__(self, open_device, close_device):
        self.open_device = open_device
        self.close_device = close_device

        self._id = self.open_device.getId()
        self._name = " ".join(self.open_device.getName().split("\\")[1:])
        self._value = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._id

    @property
    def device_class(self):
        return DEVICE_CLASS_GARAGE

    @property
    def is_closed(self):
        return self._value == 0

    @property
    def supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE

    def open_cover(self, **kwargs):
        self._value = 1
        self.open_device.setValue(1)

    def close_cover(self, **kwargs):
        self._value = 0
        self.close_device.setValue(1)