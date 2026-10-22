from __future__ import annotations

import asyncio

import pytest
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gira_homeserver import client as client_module
from custom_components.gira_homeserver.const import DOMAIN

from .fake_server import FakeHomeServer


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def entity_id(hass: HomeAssistant, domain: str, key: str) -> str:
    found = er.async_get(hass).async_get_entity_id(domain, DOMAIN, key)
    assert found, f"{domain} {key} not registered"
    return found


def state_of(hass: HomeAssistant, entity: str) -> State:
    found = hass.states.get(entity)
    assert found, f"{entity} has no state"
    return found


async def call(hass: HomeAssistant, domain: str, service: str, key: str, **data) -> None:
    await hass.services.async_call(
        domain, service, {"entity_id": entity_id(hass, domain, key), **data}, blocking=True
    )
    await asyncio.sleep(0.05)


async def test_entities_are_created_once_per_physical_device(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    registry = er.async_get(hass)
    counts = {}
    for item in registry.entities.values():
        counts[item.domain] = counts.get(item.domain, 0) + 1
    assert counts == {"light": 3, "cover": 1, "climate": 3, "switch": 1, "button": 2}


async def test_floors_areas_and_devices_are_placed(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    floors = fr.async_get(hass)
    areas = ar.async_get(hass)
    eg = floors.async_get_floor_by_name("Erdgeschoss")
    assert eg and eg.level == 0 and "EG" in eg.aliases
    wohnen = areas.async_get_area_by_name("Wohnen")
    assert wohnen and wohnen.floor_id == eg.floor_id
    outdoors = areas.async_get_area_by_name("Außen")
    assert outdoors and outdoors.floor_id is None

    devices = dr.async_get(hass)
    lamp = devices.async_get_device_by_identifier((DOMAIN, "light_10"), entry.entry_id)
    assert lamp and lamp.area_id == wohnen.id and lamp.via_device_id


async def test_existing_floors_are_reused(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    floors = fr.async_get(hass)
    mine = floors.async_create("Erdgeschoss", level=0)
    await setup(hass, entry)
    assert [f.name for f in floors.async_list_floors()].count("Erdgeschoss") == 1
    assert not floors.async_get_floor_by_name("EG")
    area = ar.async_get(hass).async_get_area_by_name("Wohnen")
    assert area and area.floor_id == mine.floor_id


async def test_deleted_areas_are_not_recreated_on_reload(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    areas = ar.async_get(hass)
    devices = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
        devices.async_update_device(device.id, area_id=None)
    area = areas.async_get_area_by_name("Wohnen")
    assert area
    areas.async_delete(area.id)

    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert areas.async_get_area_by_name("Wohnen") is None


async def test_entity_ids_include_the_room(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await setup(hass, entry)
    assert entity_id(hass, "light", "light_10") == "light.wohnen_lampe"
    assert entity_id(hass, "climate", "climate_42") == "climate.wohnen_heizung"


async def test_light_state_and_commands(
    hass: HomeAssistant, entry: MockConfigEntry, server: FakeHomeServer
) -> None:
    server.states["11"] = "1"
    await setup(hass, entry)
    assert state_of(hass, "light.wohnen_lampe").state == "on"

    await call(hass, "light", "turn_off", "light_10")
    assert server.commands[-1] == ("10", "0")
    assert state_of(hass, "light.wohnen_lampe").state == "on"

    server.push("11", "0")
    await asyncio.sleep(0.05)
    assert state_of(hass, "light.wohnen_lampe").state == "off"


async def test_dimmer_brightness(
    hass: HomeAssistant, entry: MockConfigEntry, server: FakeHomeServer
) -> None:
    server.states["21"] = "50.0"
    await setup(hass, entry)
    state = state_of(hass, entity_id(hass, "light", "dimmer_20"))
    assert state.state == "on"
    assert state.attributes["brightness"] == 128

    await call(hass, "light", "turn_on", "dimmer_20", brightness=255)
    assert server.commands[-1] == ("21", "100.0")
    await call(hass, "light", "turn_on", "dimmer_20")
    assert server.commands[-1] == ("20", "1")


async def test_cover_commands_and_assumed_state(
    hass: HomeAssistant, entry: MockConfigEntry, server: FakeHomeServer
) -> None:
    server.states["31"] = "0"
    await setup(hass, entry)
    cover = entity_id(hass, "cover", "cover_31")
    assert state_of(hass, cover).state == "open"
    assert state_of(hass, cover).attributes["assumed_state"] is True

    await call(hass, "cover", "close_cover", "cover_31")
    assert server.commands[-1] == ("31", "1")
    assert state_of(hass, cover).state == "closed"

    await call(hass, "cover", "stop_cover", "cover_31")
    assert server.commands[-1] == ("30", "0")
    assert state_of(hass, cover).state == "unknown"

    await call(hass, "cover", "open_cover", "cover_31")
    assert server.commands[-1] == ("31", "0")
    assert state_of(hass, cover).state == "open"


async def test_cover_follows_the_wall_switch(
    hass: HomeAssistant, entry: MockConfigEntry, server: FakeHomeServer
) -> None:
    server.states["31"] = "0"
    await setup(hass, entry)
    cover = entity_id(hass, "cover", "cover_31")
    server.push("31", "1")
    await asyncio.sleep(0.05)
    assert state_of(hass, cover).state == "closed"
    server.push("30", "1")
    await asyncio.sleep(0.05)
    assert state_of(hass, cover).state == "unknown"


async def test_climate(hass: HomeAssistant, entry: MockConfigEntry, server: FakeHomeServer) -> None:
    server.states.update({"40": "21.5", "41": "22.0"})
    await setup(hass, entry)
    state = state_of(hass, "climate.wohnen_heizung")
    assert state.attributes["current_temperature"] == 21.5
    assert state.attributes["temperature"] == 22.0

    await call(hass, "climate", "set_temperature", "climate_42", temperature=23)
    assert server.commands[-1] == ("42", "23.0")


async def test_door_and_permissions_are_hidden_from_assistants(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    door = entity_id(hass, "button", "button_50")
    permission = entity_id(hass, "switch", "switch_51")
    lamp = entity_id(hass, "light", "light_10")
    for assistant in ("conversation", "cloud.alexa", "cloud.google_assistant"):
        assert not async_should_expose(hass, assistant, door)
        assert not async_should_expose(hass, assistant, permission)
    assert async_should_expose(hass, "conversation", lamp)


async def test_door_button_press(
    hass: HomeAssistant, entry: MockConfigEntry, server: FakeHomeServer
) -> None:
    await setup(hass, entry)
    await call(hass, "button", "press", "button_50")
    assert server.commands == [("50", "1"), ("50", "0")]


async def test_entities_go_unavailable_when_the_link_drops(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    server: FakeHomeServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module, "RECONNECT_MIN", 30)
    await setup(hass, entry)
    await server.drop_clients()
    await asyncio.sleep(0.1)
    assert state_of(hass, "light.wohnen_lampe").state == "unavailable"


async def test_old_entities_keep_their_entity_id(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    registry = er.async_get(hass)
    entry.add_to_hass(hass)
    old_light = registry.async_get_or_create(
        "light", DOMAIN, "gira_homeserver_light_2", config_entry=entry, suggested_object_id="mine"
    )
    old_cover = registry.async_get_or_create(
        "cover", DOMAIN, "gira_homeserver_cover_5", config_entry=entry, suggested_object_id="rollo"
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert (migrated := registry.async_get(old_light.entity_id))
    assert migrated.unique_id == "light_10"
    assert (migrated := registry.async_get(old_cover.entity_id))
    assert migrated.unique_id == "cover_31"
    assert registry.async_get_entity_id("light", DOMAIN, "light_10") == "light.mine"


async def test_wrong_password_starts_reauth_and_logs_in_once(
    hass: HomeAssistant, entry: MockConfigEntry, server: FakeHomeServer
) -> None:
    server.password = "changed"
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert any(
        f["context"]["source"] == "reauth" for f in hass.config_entries.flow.async_progress()
    )
    assert server.logins == 1


async def test_unreachable_server_retries_later(
    hass: HomeAssistant, entry: MockConfigEntry, server: FakeHomeServer
) -> None:
    await server.stop()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_closes_the_connection(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await setup(hass, entry)
    client = entry.runtime_data.client
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not client.available


async def test_hidden_devices_are_not_created_and_are_removed(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    assert er.async_get(hass).async_get_entity_id("light", DOMAIN, "light_10")

    hass.config_entries.async_update_entry(entry, options={"hidden": ["light_10", "cover_31"]})
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    assert not registry.async_get_entity_id("light", DOMAIN, "light_10")
    assert not registry.async_get_entity_id("cover", DOMAIN, "cover_31")
    assert registry.async_get_entity_id("light", DOMAIN, "dimmer_20")
