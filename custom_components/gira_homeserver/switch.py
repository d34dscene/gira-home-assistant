"""Support for Gira HomeServer general switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .client import GiraClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gira HomeServer light platform."""
    client = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device in client.get_devices("switch").items():
        entities.append(GiraSwitch(client, device_id, device))

    async_add_entities(entities)

class GiraSwitch(SwitchEntity):
    """Representation of a Gira HomeServer light."""

    def __init__(self, client: GiraClient, device_id: str, device: dict):
        """Initialize the light."""
        self._client = client
        self._device = device
        self._device_id = device_id
        self._switch_id = device["slot_switch_id"]
        self._attr_name = device["name"]
        self._attr_unique_id = f"{DOMAIN}_switch_{device_id}"

    @property
    def is_on(self) -> bool|None:
        """Return true if switch is on."""
        return int(float(self._device["slot_switch_val"])) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._client.update_device_value(self._device_id, self._switch_id, "1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._client.update_device_value(self._device_id, self._switch_id, "0")
