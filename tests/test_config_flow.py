from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gira_homeserver.const import DOMAIN

from .fake_server import FakeHomeServer


def user_input(server: FakeHomeServer, **overrides) -> dict:
    return {
        "host": "127.0.0.1",
        "port": server.port,
        "username": server.username,
        "password": server.password,
        **overrides,
    }


async def start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_creates_entry(hass: HomeAssistant, server: FakeHomeServer) -> None:
    result = await start(hass)
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.gira_homeserver.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input(server)
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["username"] == server.username


async def test_wrong_password_shows_error_after_one_attempt(
    hass: HomeAssistant, server: FakeHomeServer
) -> None:
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input(server, password="nope")
    )
    assert result["errors"] == {"base": "invalid_auth"}
    assert server.logins == 1


async def test_unreachable_host_shows_error(hass: HomeAssistant, server: FakeHomeServer) -> None:
    data = user_input(server)
    await server.stop()
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_same_server_cannot_be_added_twice(
    hass: HomeAssistant, server: FakeHomeServer, entry: MockConfigEntry
) -> None:
    entry.add_to_hass(hass)
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input(server))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_the_login(
    hass: HomeAssistant, server: FakeHomeServer, entry: MockConfigEntry
) -> None:
    entry.add_to_hass(hass)
    server.password = "new"
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    with patch("custom_components.gira_homeserver.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": server.username, "password": "new"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new"


async def test_options_flow_lists_devices_and_saves_hidden(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"hidden": ["light_10"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["hidden"] == ["light_10"]
    await hass.async_block_till_done()
