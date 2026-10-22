"""Read-only smoke test against a real HomeServer. Sends no commands."""

from __future__ import annotations

import os
from collections import Counter

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_socket import socket_allow_hosts

from custom_components.gira_homeserver.const import DOMAIN

pytestmark = pytest.mark.skipif(
    not os.environ.get("GIRA_HOST"), reason="needs a real HomeServer (set GIRA_HOST)"
)


async def test_live_load_and_read(hass: HomeAssistant) -> None:
    socket_allow_hosts([os.environ["GIRA_HOST"], "127.0.0.1"])
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": os.environ["GIRA_HOST"],
            "port": int(os.environ.get("GIRA_PORT", "80")),
            "username": os.environ["GIRA_USERNAME"],
            "password": os.environ["GIRA_PASSWORD"],
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    registry = er.async_get(hass)
    areas = ar.async_get(hass)
    entities = [e for e in registry.entities.values() if e.platform == DOMAIN]
    print("\nentities per domain:", dict(Counter(e.domain for e in entities)))

    devices = dr.async_get(hass)
    unknown = []
    for item in sorted(entities, key=lambda e: e.entity_id):
        state = hass.states.get(item.entity_id)
        assert state, item.entity_id
        device = devices.async_get(item.device_id) if item.device_id else None
        area_id = item.area_id or (device.area_id if device else None)
        area = areas.async_get_area(area_id) if area_id else None
        shown = ("current_temperature", "temperature", "brightness", "current_position")
        extra = {str(k): v for k, v in state.attributes.items() if str(k) in shown}
        print(f"{item.entity_id:45} {area.name if area else '-':20} {state.state:12} {extra}")
        if state.state in ("unknown", "unavailable"):
            unknown.append(item.entity_id)

    assert not [u for u in unknown if u.split(".")[0] in ("light", "cover", "climate")], unknown
