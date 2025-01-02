"""Support for Gira HomeServer lights."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
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
    for device_id, device in client.get_devices("light").items():
        entities.append(GiraLight(client, device_id, device))
    for device_id, device in client.get_devices("dimmer").items():
        entities.append(GiraDimmer(client, device_id, device))

    async_add_entities(entities)

class GiraLight(LightEntity):
    """Representation of a Gira HomeServer light."""

    def __init__(self, client: GiraClient, device_id: str, device: dict):
        """Initialize the light."""
        self._client = client
        self._device = device
        self._device_id = device_id
        self._switch_id = device["switch_id"]
        self._attr_name = device["name"]
        self._attr_unique_id = f"{DOMAIN}_light_{device_id}"
        self._attr_color_mode = ColorMode.ONOFF
        self._attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool|None:
        """Return true if light is on."""
        return int(float(self._device["switch_val"])) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._client.update_device_value(self._device_id, self._switch_id, "1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._client.update_device_value(self._device_id, self._switch_id, "0")

class GiraDimmer(GiraLight):
    """Representation of a Gira HomeServer dimmer."""

    def __init__(self, client: GiraClient, device_id: str, device: dict):
        """Initialize the dimmer."""
        super().__init__(client, device_id, device)
        self._dim_val_id = device["dim_val_id"]
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool|None:
        """Return true if light is on."""
        return int(float(self._device["dim_val_val"])) > 0

    @property
    def brightness(self) -> int|None:
        """Return the brightness of this light between 0..255."""
        return int(float(self._device["dim_val_val"]) * 2.55)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = round(kwargs.get(ATTR_BRIGHTNESS, 255) / 2.55, 1)
        await self._client.update_device_value(self._device_id, self._dim_val_id, f"{brightness}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._client.update_device_value(self._device_id, self._dim_val_id, "0")
