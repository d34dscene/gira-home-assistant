import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN
from .ConfigurationEnumeration import ConfigurationEnumeration


class GiraConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, data):
        if data is not None:
            return self.async_create_entry(
                title="Gira Homeserver Integration", data=data
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(str(ConfigurationEnumeration.HOST.value)): str,
                    vol.Required(
                        str(ConfigurationEnumeration.PORT.value), default=80
                    ): int,
                    vol.Required(str(ConfigurationEnumeration.USERNAME.value)): str,
                    vol.Required(str(ConfigurationEnumeration.PASSWORD.value)): str,
                }
            ),
        )