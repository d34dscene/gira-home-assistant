from homeassistant.components.cover import (
    CoverEntity,
    DEVICE_CLASS_BLIND,
    SUPPORT_OPEN,
    SUPPORT_CLOSE,
    SUPPORT_SET_POSITION,
    ATTR_POSITION,
)
from .GiraEntity import GiraEntity

class GiraBlindEntity(CoverEntity, GiraEntity):
    @staticmethod
    def create(device):
        return GiraBlindEntity(device)

    def __init__(self, device):
        self.device = device
        self._id = self.device.getSensorId()
        self._name = " ".join(self.device.getName().split("\\")[1:])
        self._value = self.device.getPosition()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._id

    @property
    def device_class(self):
        return DEVICE_CLASS_BLIND

    @property
    def is_closed(self):
        return self._value == 100

    @property
    def current_cover_position(self):
        value = 0

        if self._value != None:
            value = self._value

        return 100 - value

    @property
    def supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

    def update(self):
        pass

    def open_cover(self, **kwargs):
        self.device.setPosition(0)

    def close_cover(self, **kwargs):
        self.device.setPosition(100)

    def set_cover_position(self, **kwargs):
        self._value = 100 - kwargs[ATTR_POSITION]
        self.device.setPosition(100 - kwargs[ATTR_POSITION])