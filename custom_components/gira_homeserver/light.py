"""Support for Gira HomeServer lights."""
from __future__ import annotations

import logging
from typing import Any, Optional

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
from .devices import DeviceTypeEnum, SlotTypeEnum

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gira HomeServer light platform."""
    client = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id in client.get_devices(DeviceTypeEnum.LIGHT).keys():
        entities.append(GiraLight(client, device_id))
    for device_id in client.get_devices(DeviceTypeEnum.DIMMER).keys():
        entities.append(GiraDimmer(client, device_id))

    async_add_entities(entities)

class GiraLight(LightEntity):
    """Representation of a Gira HomeServer light."""

    def __init__(self, client: GiraClient, device_id: str):
        """Initialize the light."""
        self._client = client
        self._device_id = device_id
        self._switch_id = client.get_slot_id(device_id, SlotTypeEnum.LIGHT_SWITCH)
        self._attr_name = client.devices[device_id]["name"]
        self._attr_unique_id = f"{DOMAIN}_light_{device_id}"
        self._attr_color_mode = ColorMode.ONOFF
        self._attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if light is on."""
        value = self._client.get_slot_val(self._device_id, SlotTypeEnum.LIGHT_SWITCH)
        if value is None:
            return None
        return int(float(value)) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if self._switch_id is None:
            return
        await self._client.update_device_value(self._device_id, self._switch_id, "1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        if self._switch_id is None:
            return
        await self._client.update_device_value(self._device_id, self._switch_id, "0")

class GiraDimmer(GiraLight):
    """Representation of a Gira HomeServer dimmer."""

    def __init__(self, client: GiraClient, device_id: str):
        """Initialize the dimmer."""
        self.should_poll = False
        self._client = client
        self._device_id = device_id
        self._dimmer_switch_id = client.get_slot_id(device_id, SlotTypeEnum.DIMMER_SWITCH)
        self._dimmer_brightness_id = client.get_slot_id(device_id, SlotTypeEnum.DIMMER_BRIGHTNESS)
        self._attr_name = client.get_device_name(device_id)
        self._attr_unique_id = f"{DOMAIN}_dimmer_{device_id}"
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if light is on."""
        value = self._client.get_slot_val(self._device_id, SlotTypeEnum.DIMMER_BRIGHTNESS)
        if value is None:
            return None
        return int(float(value)) > 0

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light between 0..255."""
        value = self._client.get_slot_val(self._device_id, SlotTypeEnum.DIMMER_BRIGHTNESS)
        if value is None:
            return None
        return int(float(value) * 2.55)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if self._dimmer_brightness_id is None or self._dimmer_switch_id is None:
            return

        if kwargs.get(ATTR_BRIGHTNESS) is None:
            await self._client.update_device_value(self._device_id, self._dimmer_switch_id, "1")
            return

        brightness = round(kwargs.get(ATTR_BRIGHTNESS, 255) / 2.55, 1)
        await self._client.update_device_value(self._device_id, self._dimmer_brightness_id, f"{brightness}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        if self._dimmer_brightness_id is None or self._dimmer_switch_id is None:
            return
        await self._client.update_device_value(self._device_id, self._dimmer_brightness_id, "0")
        await self._client.update_device_value(self._device_id, self._dimmer_switch_id, "0")
