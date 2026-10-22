"""Floors, areas and entity registry upkeep."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr

from .const import DOMAIN
from .data import GiraConfigEntry
from .project import Kind, Project

_LOGGER = logging.getLogger(__name__)

# INFO: Level and aliases for the floor names used in the project.
FLOORS: dict[str, tuple[int, set[str]]] = {
    "UG": (-1, {"Keller"}),
    "EG": (0, {"Erdgeschoss"}),
    "OG": (1, {"Obergeschoss"}),
}

_OLD_KINDS = {
    Kind.LIGHT: "light",
    Kind.DIMMER: "dimmer",
    Kind.COVER: "cover",
    Kind.CLIMATE: "climate",
}


def sync_areas(hass: HomeAssistant, project: Project) -> None:
    """Create missing floors and areas. Existing user choices are left alone."""
    floors = fr.async_get(hass)
    areas = ar.async_get(hass)
    places = {(d.floor, d.room) for d in project.devices if d.floor and d.room}
    for floor_name, room in sorted(places):
        floor = floors.async_get_floor_by_name(floor_name)
        if floor is None:
            level, aliases = FLOORS.get(floor_name, (None, set()))
            floor = floors.async_create(floor_name, level=level, aliases=aliases)
        area = areas.async_get_area_by_name(room)
        if area is None:
            areas.async_create(room, floor_id=floor.floor_id)
        elif area.floor_id is None:
            areas.async_update(area.id, floor_id=floor.floor_id)


def remove_hidden(hass: HomeAssistant, entry: GiraConfigEntry, hidden: set[str]) -> None:
    """Drop the devices (and their entities) the user chose to hide."""
    devices = dr.async_get(hass)
    for key in hidden:
        if device := devices.async_get_device_by_identifier((DOMAIN, key), entry.entry_id):
            devices.async_remove_device(device.id)


async def migrate_unique_ids(hass: HomeAssistant, entry: GiraConfigEntry) -> None:
    """Keep entity ids of the old integration by moving them to the new unique ids."""
    registry = er.async_get(hass)
    existing = {e.unique_id for e in registry.entities.values() if e.platform == DOMAIN}
    chosen: dict[str, str] = {}
    for device in entry.runtime_data.project.devices:
        old_kind = _OLD_KINDS.get(device.kind)
        if not old_kind or device.key in existing:
            continue
        # source ids are ordered best first, so the room entry wins over its copies
        for source_id in device.source_ids:
            if (old := f"{DOMAIN}_{old_kind}_{source_id}") in existing:
                chosen[old] = device.key
                break

    def migrate(entity: er.RegistryEntry) -> dict[str, str] | None:
        if (new := chosen.get(entity.unique_id)) is None:
            return None
        _LOGGER.info("Migrating %s to unique id %s", entity.entity_id, new)
        return {"new_unique_id": new}

    await er.async_migrate_entries(hass, entry.entry_id, migrate)
