"""Support for Gira HomeServer climate."""
from __future__ import annotations

import logging
from typing import Any, Optional


from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.components.climate import (
    ClimateEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import GiraClient
from .const import DOMAIN
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
    for device_id in client.get_devices(DeviceTypeEnum.CLIMATE).keys():
        entities.append(GiraClimate(client, device_id))

    async_add_entities(entities)

class GiraClimate(ClimateEntity):
    """Representation of a Gira HomeServer light."""

    def __init__(self, client: GiraClient, device_id: str):
        """Initialize the light."""
        self._client = client
        self._device_id = device_id
        self._target_id = client.get_slot_id(device_id, SlotTypeEnum.CLIMATE_TARGET)
        self._current_id = client.get_slot_id(device_id, SlotTypeEnum.CLIMATE_CURRENT)
        self._attr_name = client.get_device_name(device_id)
        self._attr_unique_id = f"{DOMAIN}_climate_{device_id}"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (ClimateEntityFeature.TARGET_TEMPERATURE)

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        value = self._client.get_slot_val(self._device_id, SlotTypeEnum.CLIMATE_CURRENT)
        if value is None:
            return None
        return float(value)

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        if self._target_id is None:
            return None

        value = self._client.get_slot_val(self._device_id, SlotTypeEnum.CLIMATE_TARGET)
        if value is None:
            return None
        return float(value)

    @property
    def hvac_mode(self):
        return HVACMode.HEAT

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT]

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self._target_id is None:
            return
        temperature = kwargs.get(ATTR_TEMPERATURE)
        await self._client.update_device_value(self._device_id, self._target_id, str(temperature))
