from homeassistant.helpers.entity import Entity
from homeassistant.const import TEMP_CELSIUS


class GiraThermostatEntity(Entity):
    @staticmethod
    def create(device):
        return GiraThermostatEntity(device)

    def __init__(self, device):
        self.device = device
        self._id = self.device.getId()
        self._name = " ".join(self.device.getName().split("\\")[1:])

        try:
            self._value = self.device.getValue()
        except:
            self._value = "-"

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._id

    @property
    def state(self):
        return str(self._value)

    @property
    def unit_of_measurement(self):
        return TEMP_CELSIUS

    @property
    def device_class(self):
        return "temperature"

    def update(self):
        pass