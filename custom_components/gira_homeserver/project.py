"""Turn the HomeServer client project into a clean list of physical devices.

The project lists every physical device several times (room view, "Zentral" view,
trade view, plain and slat covers). They share the same KNX tags, so tags are the
identity and duplicates are collapsed into one device.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

_LOGGER = logging.getLogger(__name__)


class Kind(StrEnum):
    LIGHT = "light"
    DIMMER = "dimmer"
    COVER = "cover"
    CLIMATE = "climate"
    SWITCH = "switch"
    BUTTON = "button"


@dataclass(frozen=True, slots=True)
class GiraDevice:
    key: str
    kind: Kind
    name: str
    floor: str | None
    room: str | None
    slots: dict[str, str]
    restricted: bool
    source_ids: tuple[str, ...]

    @property
    def feedback_tags(self) -> tuple[str, ...]:
        return tuple(self.slots.values())


@dataclass(frozen=True, slots=True)
class Project:
    devices: tuple[GiraDevice, ...]
    floors: tuple[str, ...]


# INFO: These depend on the installation.
TRADE_ROOT = "Gebäudestruktur"
NON_ROOM_FLOORS = {"Zentral"}
# Groups whose push buttons and switches must never be offered to assistants.
RESTRICTED_GROUPS = {"Türen Tor"}
BUTTON_GROUPS = {"Zentral", "Türen Tor"}
EXCLUDED_NAMES = {"Gulli-Heizung"}
RENAMES = {"AUS": "Alles aus"}
# One heating circuit is listed in several rooms, this one wins.
PREFERRED_ROOMS = (("EG", "Wohnen"),)

_FEEDBACK_SLOTS = {"switch_rm"}

# Slot sets that identify a kind, in the order they are checked. The tuple is
# also the identity of the device, the first tag is its unique id.
_SIGNATURES: tuple[tuple[Kind, tuple[str, ...]], ...] = (
    (Kind.DIMMER, ("dim_s", "dim_val")),
    (Kind.COVER, ("slot_long", "slot_short", "slot_position")),
    (Kind.CLIMATE, ("slot_targetvalue", "slot_temp_target", "slot_temp_actual")),
    (Kind.LIGHT, ("switch",)),
    (Kind.BUTTON, ("slot_switch",)),
)


@dataclass(slots=True)
class _Candidate:
    device_id: str
    kind: Kind
    name: str
    path: list[str]
    slots: dict[str, str]
    pushable: bool
    identity: tuple[str, ...]

    @property
    def tier(self) -> int:
        if self.path[0] == TRADE_ROOT and self.path[1] not in NON_ROOM_FLOORS:
            return 0
        return 1 if self.path[0] == TRADE_ROOT else 2

    @property
    def place(self) -> tuple[str, str] | None:
        return (self.path[1], self.path[2]) if self.tier == 0 and len(self.path) > 2 else None

    @property
    def group(self) -> str:
        return self.path[1] if len(self.path) > 1 else ""

    def sort_key(self) -> tuple[int, int, int, int]:
        preferred = PREFERRED_ROOMS.index(self.place) if self.place in PREFERRED_ROOMS else 99
        return (self.tier, preferred, -len(self.name), int(self.device_id))


def _clean(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()


def _classify(slots: dict[str, str]) -> tuple[Kind, tuple[str, ...]] | None:
    for kind, signature in _SIGNATURES:
        if all(slot in slots for slot in signature):
            return kind, tuple(slots[slot] for slot in signature)
    return None


def _candidates(root: ET.Element) -> list[_Candidate]:
    result = []
    for device in root.iterfind("devices/device"):
        path = [_clean(part) for part in device.attrib.get("txt", "").split("\\")]
        slots = {c.attrib["slot"]: c.attrib["tag"] for c in device.iterfind("connect")}
        if len(path) < 2 or not (classified := _classify(slots)):
            continue
        kind, identity = classified
        params = {s.attrib["parameter"]: s.attrib.get("value", "") for s in device.iterfind("set")}
        result.append(
            _Candidate(
                device_id=device.attrib["id"],
                kind=kind,
                name=path[-1],
                path=path,
                slots=slots,
                pushable="par_push" in params,
                identity=identity,
            )
        )
    return result


def _display_name(kind: Kind, name: str) -> str:
    name = RENAMES.get(name, name)
    if kind is Kind.CLIMATE:
        return "Heizung" if name in {"Heizung", "Heizen"} else f"Heizung {name}"
    return name


def parse_project(xml: bytes | str) -> Project:
    root = ET.fromstring(xml)
    floors = tuple(f.attrib["txt"] for f in root.iterfind("rooms/floor"))

    grouped: dict[tuple[Kind, tuple[str, ...]], list[_Candidate]] = defaultdict(list)
    for candidate in _candidates(root):
        grouped[(candidate.kind, candidate.identity)].append(candidate)

    devices = []
    for (kind, identity), candidates in grouped.items():
        candidates.sort(key=_Candidate.sort_key)
        best = candidates[0]
        restricted = best.group in RESTRICTED_GROUPS or any(
            c.group in RESTRICTED_GROUPS for c in candidates
        )

        if best.name in EXCLUDED_NAMES:
            continue
        if kind is Kind.BUTTON and not (
            best.pushable and any(c.group in BUTTON_GROUPS for c in candidates)
        ):
            continue
        if restricted and kind is Kind.LIGHT:
            kind = Kind.SWITCH

        place = best.place
        floor, room = place if place else (None, None)
        if floor == room:
            floor = None
        used = {slot for _, signature in _SIGNATURES for slot in signature} | _FEEDBACK_SLOTS

        devices.append(
            GiraDevice(
                key=f"{kind}_{identity[0]}",
                kind=kind,
                name=_display_name(kind, best.name),
                floor=floor,
                room=room,
                slots={s: t for s, t in best.slots.items() if s in used},
                restricted=restricted,
                source_ids=tuple(c.device_id for c in candidates),
            )
        )

    devices.sort(key=lambda d: (d.floor or "", d.room or "", d.kind, d.name))
    _LOGGER.debug("Parsed %d devices from project", len(devices))
    return Project(devices=tuple(devices), floors=floors)
