from homeassistant.helpers.entity import Entity

class GiraBasicSensorEntity(Entity):
    @staticmethod
    def create(id, name, client):
        return GiraBasicSensorEntity(id, name, client)

    def __init__(self, id, name, client):
        self.client = client

        self._id = id
        self._name = name

        try:
            self._value = client.getDeviceValue(self._id)
        except:
            self._value = "-"

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
        return str(self._value)

    def update(self):
        try:
            self._value = client.getDeviceValue(self._id)
        except:
            pass