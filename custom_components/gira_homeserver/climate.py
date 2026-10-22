"""Gira room thermostats."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
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
        "climate",
        async_add_entities,
        lambda d: GiraClimate(data, d) if d.kind is Kind.CLIMATE else None,
    )


class GiraClimate(GiraEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_target_temperature_step = 0.5

    def __init__(self, data: GiraData, device: GiraDevice) -> None:
        super().__init__(data, device)
        self._setpoint = device.slots["slot_targetvalue"]
        self._target = device.slots["slot_temp_target"]
        self._actual = device.slots["slot_temp_actual"]

    @property
    def current_temperature(self) -> float | None:
        return to_float(self._client.value(self._actual))

    @property
    def target_temperature(self) -> float | None:
        value = to_float(self._client.value(self._target))
        return value if value else None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        await self._client.set_value(self._setpoint, str(kwargs[ATTR_TEMPERATURE]))
