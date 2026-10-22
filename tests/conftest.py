from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gira_homeserver.const import DOMAIN

from .fake_server import FakeHomeServer
from .project_fixture import build_project

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def _enable(enable_custom_integrations: None, socket_enabled: None) -> None:
    return None


@pytest.fixture
async def server() -> AsyncGenerator[FakeHomeServer]:
    fake = FakeHomeServer(build_project())
    await fake.start()
    yield fake
    await fake.stop()


@pytest.fixture
def entry(server: FakeHomeServer) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"127.0.0.1:{server.port}",
        data={
            "host": "127.0.0.1",
            "port": server.port,
            "username": server.username,
            "password": server.password,
        },
    )
