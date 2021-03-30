from homeassistant.components.light import LightEntity


class GiraLightEntity(LightEntity):
    @staticmethod
    def create(device):
        return GiraLightEntity(device)

    def __init__(self, device):
        self.device = device
        self._is_on = self.device.getState()
        self._name = " ".join(self.device.getName().split("\\")[1:])
        self._id = self.device.getId()

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on

    def update(self):
        self._is_on = self.device.getState()

    @property
    def unique_id(self):
        return self._id

    def turn_on(self, **kwargs):
        self.device.turnOn()

    def turn_off(self, **kwargs):
        self.device.turnOff()