"""Support for Gira HomeServer climate."""
from __future__ import annotations

import logging
from typing import Any


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

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gira HomeServer light platform."""
    client = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device in client.get_devices("climate").items():
        entities.append(GiraClimate(client, device_id, device))

    async_add_entities(entities)

class GiraClimate(ClimateEntity):
    """Representation of a Gira HomeServer light."""

    def __init__(self, client: GiraClient, device_id: str, device: dict):
        """Initialize the light."""
        self.should_poll = False
        self._client = client
        self._device = device
        self._device_id = device_id
        self._target_id = device["slot_targetvalue_id"]
        self._current_id = device["slot_temp_actual_id"]
        self._attr_name = device["name"]
        self._attr_unique_id = f"{DOMAIN}_climate_{device_id}"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (ClimateEntityFeature.TARGET_TEMPERATURE)

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return float(self._device["slot_temp_actual_val"])

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return float(self._device["slot_targetvalue_val"])

    @property
    def hvac_mode(self):
        return HVACMode.HEAT

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT]

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        await self._client.update_device_value(self._device_id, self._target_id, str(temperature))

    async def async_update(self) -> None:
        """Update the state."""
        await self._client.fetch_device_values()
