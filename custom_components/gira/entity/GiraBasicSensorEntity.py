from homeassistant.helpers.entity import Entity

class GiraBasicSensorEntity(Entity):
    @staticmethod
    def create(sensor, client):
        return GiraBasicSensorEntity(sensor, client)

    def __init__(self, sensor, client):
        self.client = client

        self._id = sensor["id"]
        self._name = sensor["name"]
        self._value = None

        device_class = None
        unit_of_measurement = None

        if "device_class" in sensor:
            device_class = sensor["device_class"]

        if "unit_of_measurement" in sensor:
            unit_of_measurement = sensor["unit_of_measurement"]
        
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement

        self.update()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._id
    
    @property
    def should_poll(self):
        return True

    @property
    def state(self):
        return self._value

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement
    
    @property
    def device_class(self):
        return self._device_class

    @property
    def available(self):
        return self._value != None

    def update(self):
        try:
            self._value = self.client.getDeviceValue(self._id)
        except:
            pass