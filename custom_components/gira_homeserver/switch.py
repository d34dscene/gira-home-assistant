"""Gira switches that are not lights, such as door permissions."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .data import GiraConfigEntry, GiraData
from .entity import GiraEntity, add_entities, to_float
from .project import GiraDevice, Kind


async def async_setup_entry(
    hass: HomeAssistant, entry: GiraConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = entry.runtime_data
    add_entities(
        hass,
        entry,
        "switch",
        async_add_entities,
        lambda d: GiraSwitch(data, d) if d.kind is Kind.SWITCH else None,
    )


class GiraSwitch(GiraEntity, SwitchEntity):
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
