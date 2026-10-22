"""Gira HomeServer integration."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import replace

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import GiraAuthError, GiraClient, GiraConnectionError
from .const import CONF_HIDDEN, DOMAIN
from .data import GiraConfigEntry, GiraData
from .project import parse_project
from .registry import migrate_unique_ids, remove_hidden, sync_areas

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.CLIMATE, Platform.COVER, Platform.LIGHT, Platform.SWITCH]
STATE_TIMEOUT = 10


async def async_setup_entry(hass: HomeAssistant, entry: GiraConfigEntry) -> bool:
    client = GiraClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    try:
        await client.connect()
        project = parse_project(await client.fetch_project())
    except GiraAuthError as err:
        raise ConfigEntryAuthFailed("The HomeServer rejected the login") from err
    except GiraConnectionError as err:
        await client.disconnect()
        raise ConfigEntryNotReady(str(err)) from err
    except ET.ParseError as err:
        await client.disconnect()
        raise ConfigEntryError("The HomeServer project could not be read") from err

    devices = dr.async_get(hass)
    first_setup = not dr.async_entries_for_config_entry(devices, entry.entry_id)
    hub = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Gira",
        model="HomeServer",
    )
    hidden = set(entry.options.get(CONF_HIDDEN, []))
    visible = replace(project, devices=tuple(d for d in project.devices if d.key not in hidden))
    entry.runtime_data = GiraData(client, visible, hub.id, project.devices)
    remove_hidden(hass, entry, hidden)
    if first_setup:
        sync_areas(hass, visible)
    await migrate_unique_ids(hass, entry)

    async def listen() -> None:
        try:
            await client.run()
        except GiraAuthError:
            entry.async_start_reauth(hass)

    entry.async_create_background_task(hass, listen(), "gira_homeserver_listener")
    if not await client.wait_for_state(STATE_TIMEOUT):
        _LOGGER.warning("No state received from the HomeServer yet")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GiraConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.disconnect()
    return unloaded
