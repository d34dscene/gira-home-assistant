from homeassistant.components.cover import (
    CoverEntity,
    DEVICE_CLASS_BLIND,
    SUPPORT_OPEN,
    SUPPORT_CLOSE,
    SUPPORT_SET_POSITION,
    ATTR_POSITION,
)


class GiraBlindEntity(CoverEntity):
    @staticmethod
    def create(device):
        return GiraBlindEntity(device)

    def __init__(self, device):
        self.device = device
        self._id = self.device.getId()
        self._name = " ".join(self.device.getName().split("\\")[1:])
        self._value = None

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
        return self._value

    @property
    def supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

    def update(self):
        pass

    def open_cover(self, **kwargs):
        self._value = 0
        self.device.setValue(0)

    def close_cover(self, **kwargs):
        self._value = 100
        self.device.setValue(1)

    def set_cover_position(self, **kwargs):
        self.device.setValue(kwargs[ATTR_POSITION] / 100)