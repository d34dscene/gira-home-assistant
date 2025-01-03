"""Support for Gira HomeServer covers."""
from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
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
    """Set up the Gira HomeServer cover platform."""
    client = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device in client.get_devices(DeviceTypeEnum.COVER).items():
        entities.append(GiraCover(client, device_id))

    async_add_entities(entities)

class GiraCover(CoverEntity):
    """Representation of a Gira HomeServer cover."""

    def __init__(self, client: GiraClient, device_id: str):
        """Initialize the cover."""
        self._client = client
        self._device_id = device_id
        self._short_id = client.get_slot_id(device_id, SlotTypeEnum.COVER_SHORT)
        self._long_id = client.get_slot_id(device_id, SlotTypeEnum.COVER_LONG)
        self._position_id = client.get_slot_id(device_id, SlotTypeEnum.COVER_POSITION)
        self._attr_name = client.get_device_name(device_id)
        self._attr_unique_id = f"{DOMAIN}_cover_{device_id}"
        self._attr_device_class = CoverDeviceClass.BLIND
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.STOP
        )

    @property
    def current_cover_position(self) -> Optional[int]:
        """Return current position of cover."""
        value = self._client.get_slot_val(self._device_id, SlotTypeEnum.COVER_POSITION)
        if value is None:
            return None
        return 100 - int(float(value))

    @property
    def is_closed(self) -> Optional[bool]:
        """Return if the cover is closed."""
        position = self._client.get_slot_val(self._device_id, SlotTypeEnum.COVER_POSITION)
        if position is None:
            return None
        return int(float(position)) == 100

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover simluating a long press."""
        if self._long_id is None:
            return
        await self._client.update_device_value(self._device_id, self._long_id, "0")
        self._client.set_slot_val(self._device_id, SlotTypeEnum.COVER_POSITION, "0")

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover simluating a long press."""
        if self._long_id is None:
            return
        await self._client.update_device_value(self._device_id, self._long_id, "1")
        self._client.set_slot_val(self._device_id, SlotTypeEnum.COVER_POSITION, "100")

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover using the short press."""
        if self._short_id is None:
            return
        await self._client.update_device_value(self._device_id, self._short_id, "0")
        self._client.set_slot_val(self._device_id, SlotTypeEnum.COVER_POSITION, "50")

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if self._position_id is None:
            return
        position = 100 - kwargs.get(ATTR_POSITION, 0)
        await self._client.update_device_value(self._device_id, self._position_id, f"{position}")
