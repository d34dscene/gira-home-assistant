"""Gira Homeserver Integration"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .client import GiraClient, State
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.COVER,
    Platform.CLIMATE,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Gira HomeServer integration from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gira Homeserver from a config entry."""
    config = entry.data
    host = config.get("host")
    port = config.get("port", 80)
    username = config.get("username")
    password = config.get("password")

    if not host or not username or not password:
        _LOGGER.error("Missing configuration data")
        return False

    # Initialize the Client
    client = GiraClient(host, port, username, password)

    try:
        # Attempt to connect and validate authentication
        await client.connect()
        if client.state != State.LOGGED_IN:
            _LOGGER.error("Failed to log in to Gira Homeserver")
            return False
    except Exception as ex:
        _LOGGER.error("Error connecting to Gira Homeserver: %s", ex)
        return False

    # Store the client in Home Assistant's data for this domain
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = client

    # Register services
    async def handle_refresh_devices(call):
        """Handle the refresh devices service call."""
        client = hass.data[DOMAIN][entry.entry_id]
        await client.discover_devices()

    async def handle_send_raw_command(call):
        """Handle the send raw command service call."""
        client = hass.data[DOMAIN][entry.entry_id]
        command = call.data.get("command")
        try:
            await client._write(command)
        except Exception as err:
            _LOGGER.error("Error sending raw command: %s", err)

    async def handle_set_device_value(call):
        """Handle the set device value service call."""
        client = hass.data[DOMAIN][entry.entry_id]
        device_id = call.data.get("device_id")
        value = call.data.get("value")
        try:
            await client.update_device_value(device_id, value)
        except Exception as err:
            _LOGGER.error("Error setting device value: %s", err)

    hass.services.async_register(
        DOMAIN, "refresh_devices", handle_refresh_devices
    )
    hass.services.async_register(
        DOMAIN, "send_raw_command", handle_send_raw_command
    )
    hass.services.async_register(
        DOMAIN, "set_device_value", handle_set_device_value
    )

    # Forward the config entry to supported platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    client = hass.data[DOMAIN].pop(entry.entry_id, None)

    # Disconnect the client if it was initialized
    if client:
        await client.disconnect()

    return True
