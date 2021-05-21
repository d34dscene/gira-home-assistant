import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN
from .ConfigurationEnumeration import ConfigurationEnumeration


class GiraConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, info):
        if info is not None:
            return None

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(str(ConfigurationEnumeration.HOST)): str,
                    vol.Required(str(ConfigurationEnumeration.PORT)): int,
                    vol.Required(str(ConfigurationEnumeration.USERNAME)): str,
                    vol.Required(str(ConfigurationEnumeration.PASSWORD)): str,
                }
            ),
        )