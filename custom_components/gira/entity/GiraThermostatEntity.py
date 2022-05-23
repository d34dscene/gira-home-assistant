from homeassistant.components.climate import ClimateEntity, ATTR_TEMPERATURE
from homeassistant.const import TEMP_CELSIUS, HVACAction.HEATING


class GiraThermostatEntity(ClimateEntity):
    @staticmethod
    def create(device):
        return GiraThermostatEntity(device)

    def __init__(self, device):
        self.device = device
        self._id = self.device.getId()
        self._name = " ".join(self.device.getName().split("\\")[1:])
        self._value = -1

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._id

    @property
    def current_temperature(self):
        return self._value

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        return HVACAction.HEATING

    @property
    def hvac_modes(self):
        return [HVACAction.HEATING]

    @property
    def hvac_modes(self):
        return []

    @property
    def supported_features(self):
        return 0

    def set_temperature(self, **kwargs):
        self._value = kwargs[ATTR_TEMPERATURE]
        self.device.setValue(self._value)

    def update(self):
        try:
            value = self.device.getValue()
            if value == None:
                self._value = -1
            else:
                self._value = value
        except:
            pass