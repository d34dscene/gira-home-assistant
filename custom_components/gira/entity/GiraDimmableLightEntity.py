from homeassistant.components.light import (
    LightEntity,
    SUPPORT_BRIGHTNESS,
    ATTR_BRIGHTNESS,
)
from .GiraEntity import GiraEntity

class GiraDimmableLightEntity(LightEntity, GiraEntity):
    @staticmethod
    def create(device):
        return GiraDimmableLightEntity(device)

    def __init__(self, device):
        self.device = device
        self._id = self.device.getActuatorId()
        self._name = " ".join(self.device.getName().split("\\")[1:])

        value = 0

        try:
            brightness = self.device.getBrightness()
            if brightness != None:
                value = brightness
        except:
            pass
    
        self._value = value


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
        return self._name

    def update(self):
        pass

    def turn_on(self, **kwargs):
        self._value = round(kwargs.get(ATTR_BRIGHTNESS, 255) / 2.55, 1)
        self.device.setBrightness(self._value)

    def turn_off(self, **kwargs):
        self._value = 0
        self.device.setBrightness(0)

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS