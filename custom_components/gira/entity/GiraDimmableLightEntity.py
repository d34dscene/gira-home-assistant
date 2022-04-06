from homeassistant.components.light import (
    LightEntity,
    SUPPORT_BRIGHTNESS,
    ATTR_BRIGHTNESS,
)


class GiraDimmableLightEntity(LightEntity):
    @staticmethod
    def create(device):
        return GiraDimmableLightEntity(device)

    def __init__(self, device):
        self.device = device
        self._id = self.device.getId()
        self._name = " ".join(self.device.getName().split("\\")[1:])

        try:
            self._value = self.device.getValue()
        except:
            self._value = 0

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._id

    @property
    def is_on(self):
        return self._value > 0

    @property
    def brightness(self):
        return self._value * 2.55

    @property
    def unique_id(self):
        return self._id

    def update(self):
        pass

    def turn_on(self, **kwargs):
        self._value = round(kwargs.get(ATTR_BRIGHTNESS, 255) * 1 / 255, 1)
        self.device.setValue(self._value)

    def turn_off(self, **kwargs):
        self._value = 0
        self.device.setValue(0)

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS