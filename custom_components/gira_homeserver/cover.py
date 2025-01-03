"""Support for Gira HomeServer covers."""
from __future__ import annotations

import logging
from typing import Any

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

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gira HomeServer cover platform."""
    client = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for device_id, device in client.get_devices("cover").items():
        entities.append(GiraCover(client, device_id, device))

    async_add_entities(entities)

class GiraCover(CoverEntity):
    """Representation of a Gira HomeServer cover."""

    def __init__(self, client: GiraClient, device_id: str, device: dict):
        """Initialize the cover."""
        self.should_poll = False
        self._client = client
        self._device = device
        self._device_id = device_id
        self._long_id = device["slot_long_id"]
        self._short_id = device["slot_short_id"]
        self._position_id = device["slot_position_id"]
        self._attr_name = device["name"]
        self._attr_unique_id = f"{DOMAIN}_cover_{device_id}"
        self._attr_device_class = CoverDeviceClass.BLIND
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.STOP
        )

    @property
    def current_cover_position(self) -> int|None:
        """Return current position of cover."""
        value = 0
        if self._device["slot_position_val"] is not None:
            value = int(float(self._device["slot_position_val"]))
        return 100 - value

    @property
    def is_closed(self) -> bool|None:
        """Return if the cover is closed."""
        return self._device["slot_position_val"] == "100"

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover simluating a long press."""
        await self._client.update_device_value(self._device_id, self._long_id, "0")
        self._device["slot_position_val"] = "0"

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover simluating a long press."""
        await self._client.update_device_value(self._device_id, self._long_id, "1")
        self._device["slot_position_val"] = "100"

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover using the short press."""
        await self._client.update_device_value(self._device_id, self._short_id, "0")
        self._device["slot_position_val"] = "50"

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = 100 - kwargs.get(ATTR_POSITION, 0)
        await self._client.update_device_value(self._device_id, self._position_id, f"{position}")

    async def async_update(self) -> None:
        """Update the state."""
        await self._client.fetch_device_values()
