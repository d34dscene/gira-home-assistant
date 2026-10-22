"""Runtime data of a config entry."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .client import GiraClient
from .project import GiraDevice, Project


@dataclass
class GiraData:
    client: GiraClient
    project: Project
    hub_id: str
    all_devices: tuple[GiraDevice, ...]


type GiraConfigEntry = ConfigEntry[GiraData]
