# Gira HomeServer for Home Assistant

Local push integration for the Gira HomeServer. Talks to the box over the same
protocol the official app uses. No cloud.

Supports lights, dimmers, roller shutters, room thermostats, push buttons and
switches. Needs Home Assistant 2026.10 or newer.

## Install

With HACS, add this repo as a custom repository, install it and restart.

Manually, copy `custom_components/gira_homeserver` into the `custom_components`
folder of your Home Assistant config. For Docker that is the folder you mount
as `/config`.

Then go to `Settings › Devices & services › Add integration › Gira HomeServer`
and enter host, port, username and password.

## What you get

- Floors and areas are created from the project (for example floor `EG`, area
  `Wohnen`) and every device is placed in its room.
- The project lists each physical device several times (room, "Zentral", trade
  view, covers with and without slats). They share the same KNX tags, so they
  are merged into one device.
- Entity ids carry the room, for example `light.wohnen_spots_1`.
- State is pushed from the HomeServer. If the link drops, entities turn
  unavailable and the integration reconnects.
- A wrong password is tried once, never in a loop. You get a reauth prompt.

## Covers

The HomeServer reports no real blind position and absolute positioning did not
work reliably on the actuators here (a position command made a blind do a full
run first). So covers offer open, close and stop only. State is assumed from the
last move command, which also catches the app and wall switches. After a stop
the state is unknown until the next open or close.

## Hiding devices

Project entries that are not wired (spare actuator channels) can be hidden under
`Settings › Devices & services › Gira HomeServer › Configure`. Hidden devices are
removed from Home Assistant and stay hidden after restarts.

## Doors and permissions

Everything in the trade group `Türen Tor` (door opener, permission switches) is
hidden from all assistants (Assist, Alexa, Google) when it is first created.
You can still press and toggle it from the UI. Exposing it later is a manual
choice under `Settings › Voice assistants`.

## Adapting it to another house

The installation specific bits sit at the top of `project.py` (group names,
excluded devices, preferred room for shared circuits) and in `registry.py`
(floor levels and aliases).

## Upgrading from the first version

Old entities are matched to the new devices and keep their entity ids.
Duplicate entities from the old version that now map to the same device stay
behind as unavailable. Delete them in the UI.

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run ty check
uv run pytest
```

Tests run against an in-process fake HomeServer. `tests/test_live.py` is a
read-only smoke test against a real box. It sends no commands and is skipped
unless `GIRA_HOST`, `GIRA_PORT`, `GIRA_USERNAME` and `GIRA_PASSWORD` are set.
