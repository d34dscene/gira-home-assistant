"""Gira covers (roller shutters).

The HomeServer reports no real position. Moving is done with the long object
(1 down, 0 up) and stopped with the short object. Absolute positioning is not
reliable on the actuators seen so far, so only open, close and stop are offered.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
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
        "cover",
        async_add_entities,
        lambda d: GiraCover(data, d) if d.kind is Kind.COVER else None,
    )


class GiraCover(GiraEntity, CoverEntity):
    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_assumed_state = True
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )

    def __init__(self, data: GiraData, device: GiraDevice) -> None:
        super().__init__(data, device)
        self._short = device.slots["slot_short"]
        self._long = device.slots["slot_long"]
        self._stopped = False

    async def async_added_to_hass(self) -> None:
        # Registered first so the flag is set before the state is written.
        self.async_on_remove(self._client.subscribe([self._short], self._on_stop))
        self.async_on_remove(self._client.subscribe([self._long], self._on_move))
        await super().async_added_to_hass()

    def _on_stop(self) -> None:
        self._stopped = True

    def _on_move(self) -> None:
        self._stopped = False

    @property
    def is_closed(self) -> bool | None:
        if self._stopped:
            return None
        value = to_float(self._client.value(self._long))
        return None if value is None else value > 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._client.set_value(self._long, "0")

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._client.set_value(self._long, "1")

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._client.set_value(self._short, "0")
