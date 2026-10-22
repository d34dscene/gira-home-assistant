"""Config flow for the Gira HomeServer."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import probatio
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .client import GiraAuthError, GiraClient, GiraConnectionError
from .const import CONF_HIDDEN, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): str,
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): int,
        probatio.Required(CONF_USERNAME): str,
        probatio.Required(CONF_PASSWORD): str,
    }
)
REAUTH_SCHEMA = probatio.Schema(
    {probatio.Required(CONF_USERNAME): str, probatio.Required(CONF_PASSWORD): str}
)


async def _check_login(hass: HomeAssistant, data: Mapping[str, Any]) -> str | None:
    """Log in once and return an error key, or None when it worked."""
    client = GiraClient(
        async_get_clientsession(hass),
        data[CONF_HOST],
        data[CONF_PORT],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )
    try:
        await client.connect()
    except GiraAuthError:
        return "invalid_auth"
    except GiraConnectionError:
        return "cannot_connect"
    finally:
        await client.disconnect()
    return None


class GiraConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GiraOptionsFlow:
        return GiraOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()
            if error := await _check_login(self.hass, user_input):
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=f"Gira HomeServer ({user_input[CONF_HOST]})", data=user_input
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            if error := await _check_login(self.hass, {**entry.data, **user_input}):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                REAUTH_SCHEMA, user_input or {CONF_USERNAME: entry.data[CONF_USERNAME]}
            ),
            errors=errors,
        )


class GiraOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        if self.config_entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="not_loaded")
        options = [
            SelectOptionDict(value=d.key, label=f"{d.room or '-'}: {d.name} ({d.kind})")
            for d in self.config_entry.runtime_data.all_devices
        ]
        schema = probatio.Schema(
            {
                probatio.Optional(CONF_HIDDEN): SelectSelector(
                    SelectSelectorConfig(
                        options=options, multiple=True, mode=SelectSelectorMode.LIST
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, self.config_entry.options),
        )
