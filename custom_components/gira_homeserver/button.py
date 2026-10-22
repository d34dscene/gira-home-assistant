"""Gira push buttons such as the door opener."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .data import GiraConfigEntry, GiraData
from .entity import GiraEntity, add_entities
from .project import GiraDevice, Kind


async def async_setup_entry(
    hass: HomeAssistant, entry: GiraConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = entry.runtime_data
    add_entities(
        hass,
        entry,
        "button",
        async_add_entities,
        lambda d: GiraButton(data, d) if d.kind is Kind.BUTTON else None,
    )


class GiraButton(GiraEntity, ButtonEntity):
    def __init__(self, data: GiraData, device: GiraDevice) -> None:
        super().__init__(data, device)
        self._tag = device.slots["slot_switch"]

    async def async_press(self) -> None:
        await self._client.set_value(self._tag, "1")
        await self._client.set_value(self._tag, "0")
