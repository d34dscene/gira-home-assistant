"""Shared base for Gira entities."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.homeassistant.exposed_entities import (
    KNOWN_ASSISTANTS,
    async_expose_entity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .data import GiraConfigEntry, GiraData
from .project import GiraDevice, Kind

MODELS = {
    Kind.LIGHT: "Switch actuator",
    Kind.DIMMER: "Dimmer",
    Kind.COVER: "Blind actuator",
    Kind.CLIMATE: "Room thermostat",
    Kind.SWITCH: "Switch",
    Kind.BUTTON: "Push button",
}


def to_float(value: str | None) -> float | None:
    try:
        return None if value is None else float(value)
    except ValueError:
        return None


class GiraEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = None

    def __init__(self, data: GiraData, device: GiraDevice) -> None:
        self._client = data.client
        self.device = device
        self._attr_unique_id = device.key
        info = DeviceInfo(
            identifiers={(DOMAIN, device.key)},
            name=device.name,
            manufacturer="Gira",
            model=MODELS[device.kind],
            via_device_id=data.hub_id,
        )
        if device.room:
            info["suggested_area"] = device.room
        self._attr_device_info = info

    @property
    def available(self) -> bool:
        return self._client.available

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._client.subscribe(self.device.feedback_tags, self.async_write_ha_state)
        )
        self.async_on_remove(self._client.subscribe_availability(self.async_write_ha_state))


def add_entities(
    hass: HomeAssistant,
    entry: GiraConfigEntry,
    domain: str,
    async_add_entities: AddEntitiesCallback,
    build: Callable[[GiraDevice], GiraEntity | None],
) -> None:
    """Add entities for every device the builder accepts.

    New entities are registered first so the entity id carries the room. Restricted
    ones are hidden from all assistants at that moment.
    """
    registry = er.async_get(hass)
    entities: list[GiraEntity] = []
    for device in entry.runtime_data.project.devices:
        if (entity := build(device)) is None:
            continue
        entities.append(entity)
        if registry.async_get_entity_id(domain, DOMAIN, device.key):
            continue
        object_id = f"{device.room} {device.name}" if device.room else device.name
        created = registry.async_get_or_create(
            domain, DOMAIN, device.key, config_entry=entry, suggested_object_id=object_id
        )
        if device.restricted:
            for assistant in KNOWN_ASSISTANTS:
                async_expose_entity(hass, assistant, created.entity_id, False)
    async_add_entities(entities)
