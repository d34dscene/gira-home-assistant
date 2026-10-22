"""Gira lights and dimmers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .data import GiraConfigEntry, GiraData
from .entity import GiraEntity, add_entities, to_float
from .project import GiraDevice, Kind

BRIGHTNESS_SCALE = (1, 255)


async def async_setup_entry(
    hass: HomeAssistant, entry: GiraConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = entry.runtime_data

    def build(device: GiraDevice) -> GiraEntity | None:
        if device.kind is Kind.LIGHT:
            return GiraLight(data, device)
        if device.kind is Kind.DIMMER:
            return GiraDimmer(data, device)
        return None

    add_entities(hass, entry, "light", async_add_entities, build)


class GiraLight(GiraEntity, LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, data: GiraData, device: GiraDevice) -> None:
        super().__init__(data, device)
        self._command = device.slots["switch"]
        self._feedback = device.slots.get("switch_rm", self._command)

    @property
    def is_on(self) -> bool | None:
        value = to_float(self._client.value(self._feedback))
        return None if value is None else value > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._client.set_value(self._command, "1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.set_value(self._command, "0")


class GiraDimmer(GiraEntity, LightEntity):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, data: GiraData, device: GiraDevice) -> None:
        super().__init__(data, device)
        self._switch = device.slots["dim_s"]
        self._level = device.slots["dim_val"]

    @property
    def is_on(self) -> bool | None:
        value = to_float(self._client.value(self._level))
        return None if value is None else value > 0

    @property
    def brightness(self) -> int | None:
        value = to_float(self._client.value(self._level))
        if value is None:
            return None
        return round(percentage_to_ranged_value(BRIGHTNESS_SCALE, value))

    async def async_turn_on(self, **kwargs: Any) -> None:
        if (brightness := kwargs.get(ATTR_BRIGHTNESS)) is None:
            await self._client.set_value(self._switch, "1")
            return
        percent = ranged_value_to_percentage(BRIGHTNESS_SCALE, brightness)
        await self._client.set_value(self._level, f"{percent:.1f}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.set_value(self._switch, "0")
