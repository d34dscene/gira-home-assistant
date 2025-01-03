"""Support for Gira HomeServer general switches."""
from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.switch import (
    SwitchEntity,
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
    for device_id in client.get_devices(DeviceTypeEnum.SWITCH).keys():
        entities.append(GiraSwitch(client, device_id))

    async_add_entities(entities)

class GiraSwitch(SwitchEntity):
    """Representation of a Gira HomeServer light."""

    def __init__(self, client: GiraClient, device_id: str):
        """Initialize the light."""
        self._client = client
        self._device_id = device_id
        self._switch_id = client.get_slot_id(device_id, SlotTypeEnum.GENERAL_SWITCH)
        self._attr_name = client.get_device_name(device_id)
        self._attr_unique_id = f"{DOMAIN}_switch_{device_id}"

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if switch is on."""
        value = self._client.get_slot_val(self._device_id, SlotTypeEnum.GENERAL_SWITCH)
        if value is None:
            return None
        return int(float(value)) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self._switch_id is None:
            return
        await self._client.update_device_value(self._device_id, self._switch_id, "1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self._switch_id is None:
            return
        await self._client.update_device_value(self._device_id, self._switch_id, "0")
