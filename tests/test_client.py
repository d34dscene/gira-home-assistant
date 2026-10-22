from __future__ import annotations

import asyncio

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.gira_homeserver import client as client_module
from custom_components.gira_homeserver.client import (
    GiraAuthError,
    GiraClient,
    GiraConnectionError,
)

from .fake_server import FakeHomeServer


def make_client(hass: HomeAssistant, server: FakeHomeServer, password: str | None = None):
    return GiraClient(
        async_get_clientsession(hass),
        "127.0.0.1",
        server.port,
        server.username,
        password or server.password,
    )


async def test_connect_loads_state_and_project(hass: HomeAssistant, server: FakeHomeServer) -> None:
    server.states["10"] = "1.0"
    client = make_client(hass, server)
    await client.connect()
    task = asyncio.create_task(client.run())
    assert await client.wait_for_state(2)
    assert client.value("10") == "1.0"
    assert b"<project>" in await client.fetch_project()
    await client.disconnect()
    await task


async def test_every_push_notifies_subscribed_tags_only(
    hass: HomeAssistant, server: FakeHomeServer
) -> None:
    client = make_client(hass, server)
    await client.connect()
    task = asyncio.create_task(client.run())
    assert await client.wait_for_state(2)
    calls: list[str] = []
    client.subscribe(["11"], lambda: calls.append("11"))
    server.push("10", "1")
    server.push("11", "1")
    server.push("11", "1")
    await asyncio.sleep(0.1)
    assert calls == ["11", "11"]
    await client.disconnect()
    await task


async def test_set_value_reaches_the_server(hass: HomeAssistant, server: FakeHomeServer) -> None:
    client = make_client(hass, server)
    await client.connect()
    task = asyncio.create_task(client.run())
    await client.set_value("10", "1")
    await asyncio.sleep(0.1)
    assert server.commands == [("10", "1")]
    await client.disconnect()
    await task


async def test_wrong_password_fails_once_without_retry(
    hass: HomeAssistant, server: FakeHomeServer
) -> None:
    client = make_client(hass, server, password="wrong")
    with pytest.raises(GiraAuthError):
        await client.connect()
    assert server.logins == 1


async def test_unreachable_host_raises_connection_error(
    hass: HomeAssistant, server: FakeHomeServer
) -> None:
    client = make_client(hass, server)
    await server.stop()
    with pytest.raises(GiraConnectionError):
        await client.connect()


async def test_reconnects_after_link_drop(
    hass: HomeAssistant, server: FakeHomeServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(client_module, "RECONNECT_MIN", 0.05)
    client = make_client(hass, server)
    await client.connect()
    task = asyncio.create_task(client.run())
    states: list[bool] = []
    client.subscribe_availability(lambda: states.append(client.available))
    await server.drop_clients()
    await asyncio.sleep(0.4)
    assert states == [False, True]
    server.push("10", "1")
    await asyncio.sleep(0.1)
    assert client.value("10") == "1"
    assert server.logins == 2
    await client.disconnect()
    await task
