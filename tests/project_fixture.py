"""Synthetic HomeServer project with the quirks of a real one."""

from __future__ import annotations

from xml.sax.saxutils import quoteattr

ROOMS = """
<rooms>
  <floor uid="1" parent="0" txt="UG" /><room uid="2" parent="1" txt="Keller" />
  <floor uid="3" parent="0" txt="EG" /><room uid="4" parent="3" txt="Wohnen" />
  <floor uid="5" parent="0" txt="OG" /><room uid="6" parent="5" txt="Schlafen" />
  <floor uid="7" parent="0" txt="Außen" /><room uid="8" parent="7" txt="Außen" />
  <floor uid="9" parent="0" txt="Zentral" /><room uid="10" parent="9" txt="Zentral" />
</rooms>
"""

LIGHT_TAGS = {"switch": "10", "switch_rm": "11"}
DIMMER_TAGS = {"dim_s": "20", "dim_val": "21"}
COVER_TAGS = {"slot_short": "30", "slot_long": "31", "slot_position": "32"}
CLIMATE_TAGS = {"slot_targetvalue": "42", "slot_temp_target": "41", "slot_temp_actual": "40"}
DOOR_TAG = "50"
PERMISSION_TAG = "51"
ALL_OFF_TAG = "60"


def _device(device_id: int, path: str, slots: dict[str, str], params: dict[str, str] | None = None):
    connects = "".join(f'<connect slot="{s}" tag="{t}" />' for s, t in slots.items())
    sets = "".join(
        f'<set parameter="{k}" value={quoteattr(v)} />' for k, v in (params or {}).items()
    )
    return f'<device id="{device_id}" txt={quoteattr(path)}>{connects}{sets}</device>'


def build_project() -> bytes:
    devices = [
        _device(1, r"Gebäudestruktur\EG\Wohnen\Lampe", LIGHT_TAGS),
        _device(2, r"Gebäudestruktur\Zentral\Zentral\Wohnen EG Lampe", LIGHT_TAGS),
        _device(3, r"Gebäudestruktur\EG\Wohnen\Spots", DIMMER_TAGS),
        _device(4, r"Gebäudestruktur\Zentral\Zentral\Spots EG", DIMMER_TAGS),
        _device(
            5, r"Gebäudestruktur\EG\Wohnen\Jalousie", {**COVER_TAGS, "slot_position_lamelle": "33"}
        ),
        _device(6, r"Gebäudestruktur\EG\Wohnen\Jalousie 1 ", COVER_TAGS),
        _device(7, r"Gebäudestruktur\UG\Keller\Heizung", CLIMATE_TAGS),
        _device(8, r"Gebäudestruktur\EG\Wohnen\Heizung", CLIMATE_TAGS),
        _device(
            9,
            r"Gebäudestruktur\OG\Schlafen\Heizung",
            {"slot_targetvalue": "45", "slot_temp_target": "44", "slot_temp_actual": "43"},
        ),
        _device(10, r"Gewerke\Türen Tor\Haustüre", {"slot_switch": DOOR_TAG}, {"par_push": "open"}),
        _device(
            11,
            r"Gewerke\Türen Tor\Anna",
            {"switch": PERMISSION_TAG, "switch_rm": PERMISSION_TAG},
        ),
        _device(
            12,
            r"Gebäudestruktur\Zentral\Zentral\AUS",
            {"slot_switch": ALL_OFF_TAG},
            {"par_push": "AUS"},
        ),
        _device(13, r"Gewerke\Zentral\Alles", {"slot_switch": ALL_OFF_TAG}, {"par_push": "AUS"}),
        _device(
            14, r"Gebäudestruktur\Außen\Außen\Gulli-Heizung", {"switch": "70", "switch_rm": "71"}
        ),
        _device(15, r"Gebäudestruktur\Außen\Außen\Terrasse", {"switch": "72", "switch_rm": "73"}),
        _device(
            16,
            r"Gewerke\Heizung\Hobby",
            {"slot_targetvalue": "48", "slot_temp_target": "47", "slot_temp_actual": "46"},
        ),
        _device(17, r"Gebäudestruktur\EG\Wohnen\Status", {"slot_state2": "80"}),
    ]
    body = "".join(devices)
    xml = (
        f'<?xml version="1.0" encoding="utf-8"?><project>{ROOMS}<devices>{body}</devices></project>'
    )
    return xml.encode()
