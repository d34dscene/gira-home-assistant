from __future__ import annotations

import pytest

from custom_components.gira_homeserver.project import GiraDevice, Kind, Project, parse_project

from .project_fixture import build_project


@pytest.fixture
def project() -> Project:
    return parse_project(build_project())


def by_name(project: Project, kind: Kind, name: str) -> GiraDevice:
    return next(d for d in project.devices if d.kind is kind and d.name == name)


def test_duplicates_collapse_to_one_device(project: Project) -> None:
    lights = [d for d in project.devices if d.kind is Kind.LIGHT]
    assert sorted(d.name for d in lights) == ["Lampe", "Terrasse"]
    assert len([d for d in project.devices if d.kind is Kind.DIMMER]) == 1
    assert len([d for d in project.devices if d.kind is Kind.COVER]) == 1


def test_room_entry_wins_and_keeps_all_source_ids(project: Project) -> None:
    lamp = by_name(project, Kind.LIGHT, "Lampe")
    assert (lamp.floor, lamp.room) == ("EG", "Wohnen")
    assert lamp.source_ids == ("1", "2")
    assert lamp.key == "light_10"


def test_most_specific_name_and_no_tilt_slot(project: Project) -> None:
    cover = by_name(project, Kind.COVER, "Jalousie 1")
    assert "slot_position_lamelle" not in cover.slots
    assert set(cover.source_ids) == {"5", "6"}


def test_shared_heating_circuit_goes_to_preferred_room(project: Project) -> None:
    shared = next(d for d in project.devices if d.kind is Kind.CLIMATE and d.room == "Wohnen")
    assert set(shared.source_ids) == {"7", "8"}
    assert shared.name == "Heizung"
    assert not any(d.room == "Keller" for d in project.devices)


def test_trade_only_heating_has_no_place_and_a_clear_name(project: Project) -> None:
    hobby = by_name(project, Kind.CLIMATE, "Heizung Hobby")
    assert (hobby.floor, hobby.room) == (None, None)


def test_outdoor_room_has_no_floor(project: Project) -> None:
    terrace = by_name(project, Kind.LIGHT, "Terrasse")
    assert (terrace.floor, terrace.room) == (None, "Außen")


def test_door_and_permissions_are_restricted(project: Project) -> None:
    door = by_name(project, Kind.BUTTON, "Haustüre")
    permission = by_name(project, Kind.SWITCH, "Anna")
    assert door.restricted
    assert permission.restricted
    assert not any(d.restricted for d in project.devices if d.kind is Kind.LIGHT)


def test_central_button_is_merged_and_renamed(project: Project) -> None:
    assert by_name(project, Kind.BUTTON, "Alles aus").source_ids == ("12", "13")


def test_excluded_and_status_devices_are_skipped(project: Project) -> None:
    names = {d.name for d in project.devices}
    assert "Gulli-Heizung" not in names
    assert "Status" not in names
