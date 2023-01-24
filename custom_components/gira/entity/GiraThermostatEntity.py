from homeassistant.components.climate import ClimateEntity, ATTR_TEMPERATURE, ClimateEntityFeature
from homeassistant.const import TEMP_CELSIUS
from homeassistant.components.climate.const import HVACMode
from .GiraEntity import GiraEntity

class GiraThermostatEntity(ClimateEntity, GiraEntity):
    @staticmethod
    def create(device):
        return GiraThermostatEntity(device)

    def __init__(self, device):
        self.device = device
        self._id = self.device.getSensorId()
        self._name = " ".join(self.device.getName().split("\\")[1:])
        self._value = self.device.getCurrentTemperature()
        self._set_value = self.device.getSetTemperature()

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
    def target_temperature(self):
        return self._set_value

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        return HVACMode.HEAT

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT]

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE

    def set_temperature(self, **kwargs):
        self._set_value = kwargs[ATTR_TEMPERATURE]
        self.device.setTemperature(self._set_value)

    def update(self):
        try:
            current_value = self.device.getCurrentTemperature()
            if current_value == None:
                self._value = -1
            else:
                self._value = current_value
            
            set_value = self.device.getSetTemperature()
            if set_value == None:
                self._set_value = -1
            else:
                self._set_value = current_value
        except:
            pass