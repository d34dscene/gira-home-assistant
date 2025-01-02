import asyncio
import hashlib
import logging
from typing import Dict, Optional
from enum import Enum

import aiohttp
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.gira_homeserver.devices import DeviceParser

_LOGGER = logging.getLogger(__name__)

class State(Enum):
    DISCONNECTED = 1
    CONNECTED = 2
    LOGGED_IN = 3

class GiraClient:
    """Gira HomeServer client."""

    def __init__(self, host: str, port: int, username: str, password: str):
        """Initialize the client."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.state = State.DISCONNECTED
        self.devices: Dict[str, dict] = {}
        self._token: Optional[str] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()
        self._shutdown = False

    async def connect(self, *, retry: bool = True) -> None:
        """Connect to the Gira HomeServer."""
        while not self._shutdown:
            try:
                self._reader, self._writer = await asyncio.open_connection(
                    self.host, self.port
                )
                self.state = State.CONNECTED
                await self._login()

                if self.state == State.LOGGED_IN:
                    asyncio.create_task(self._monitor())
                    return
                else:
                    _LOGGER.error("Login failed")
                break
            except asyncio.TimeoutError as err:
                _LOGGER.error("Timeout connecting to Gira HomeServer: %s", err)
                self.state = State.DISCONNECTED
                if not retry:
                    raise ConfigEntryNotReady from err

            except Exception as err:
                _LOGGER.error("Failed to connect to Gira HomeServer: %s", err)
                self.state = State.DISCONNECTED
                if not retry:
                    raise ConfigEntryNotReady from err

            if retry:
                await asyncio.sleep(3)
            else:
                break

    async def disconnect(self) -> None:
        """Disconnect from the Gira HomeServer."""
        self._shutdown = True
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
                _LOGGER.debug("Successfully disconnected from Gira HomeServer")
            except Exception:
                _LOGGER.exception("Error during disconnect")
        self.state = State.DISCONNECTED

    async def _login(self):
        await self._write("GET /QUAD/LOGIN \r\n\r\n")
        while True:
            action, messages = await self._read()
            _LOGGER.debug(f"Action: {action}")

            if action == 100:
                """Request connection"""
                await self._write(f"90|{self.username}|")
            elif action == 91:
                """Generate hash"""
                salt = messages[0][0]
                hash = self._generate_hash(self.username, self.password, salt)
                await self._write(f"92|{hash}|")
            elif action == 93:
                """Login successful"""
                self.state = State.LOGGED_IN
                self._token = str(messages[0][0])
                _LOGGER.info("Successfully logged in to Gira HomeServer")
                await self._write("94||") # Request device values
            elif action == 2:
                _LOGGER.debug(f"Got {len(messages)} connection ids and values")
                init_val = {}
                for message in messages:
                    if len(message) == 3:
                        connection_id, value = message[0], message[1]
                        init_val[connection_id] = value
                await self.discover_devices(init_val=init_val)
                break
            else:
                _LOGGER.warning(f"Unhandled action during login: {action}")

    async def _monitor(self) -> None:
        """Monitor for updates from the server."""
        while not self._shutdown:
            try:
                action, messages = await self._read()
                _LOGGER.debug(f"Monitor received action {action} with {len(messages)} messages")

                if action != 1:
                    _LOGGER.debug(f"Monitor received non-update action {messages}")
                    continue

                for connection_id, value, _ in messages:
                    # Find device and field that uses this connection ID
                    for device_id, device in self.devices.items():
                        for key, device_connection_id in device.items():
                            if key.endswith("_id") and device_connection_id == connection_id:
                                value_key = key.replace("_id", "_val")
                                device[value_key] = value
                                _LOGGER.debug(
                                    "Device %s (%s) connection %s updated: %s",
                                    device_id,
                                    value_key,
                                    connection_id,
                                    value
                                )
                                break
            except Exception:
                _LOGGER.exception("Error in monitor loop")
                await asyncio.sleep(1)

    async def _read(self):
        """Safely read data using a lock to prevent concurrent read access."""
        if not self._reader:
            raise ConnectionError("Reader is not initialized")

        async with self._lock:
            data = await self._reader.read(2048)
            if not data:
                raise ConnectionError("No data received")

            raw_messages = data.decode().strip("\x00").split("|")
            if not raw_messages or len(raw_messages) < 2:
                raise ConnectionError("Malformed response data")

            action = int(raw_messages[0])
            messages = [
                raw_messages[i:i+3] for i in range(1, len(raw_messages), 3)
            ]
            return action, messages


    async def _write(self, data):
        if not self._writer:
            _LOGGER.error("Writer is not initialized")
            return

        if self.state not in [State.CONNECTED, State.LOGGED_IN]:
            _LOGGER.error("Client is not connected")
            return

        try:
            self._writer.write((data + "\x00").encode())
            await self._writer.drain()
        except Exception:
            _LOGGER.exception("Error sending message")

    async def discover_devices(self, init_val: dict):
        """Discover devices from the Gira HomeServer."""
        if self.state != State.LOGGED_IN or not self._token:
            _LOGGER.error("Not connected")
            return

        _LOGGER.debug("Discovering devices...")
        url = f"http://{self.host}:{self.port}/quad/client/client_project.xml?{self._token}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                xml = await response.text()
                parser = DeviceParser()
                self.devices = parser.parse(xml)

        for device_id, device in self.devices.items():
            for key, connection_id in device.items():
                if key.endswith("_id") and connection_id in init_val:
                    value_key = key.replace("_id", "_val")
                    device[value_key] = init_val[connection_id]
                    _LOGGER.debug(
                        "Device %s (%s) connection %s updated: %s",
                        device_id,
                        value_key,
                        connection_id,
                        init_val[connection_id]
                    )

    def get_devices(self, type: str) -> dict:
        """Get list of devices by type."""
        if type:
            return {id: device for id, device in self.devices.items() if device["type"] == type}
        else:
            return self.devices

    async def update_device_value(self, device_id: str, connection_id: str, value: str) -> None:
        """Update device value."""
        if self.state != State.LOGGED_IN:
            _LOGGER.error("Not connected")
            return None

        if device_id not in self.devices:
            _LOGGER.warning("Device %s not found", device_id)
            return None

        device = self.devices[device_id]
        try:
            await self._write(f"1|{connection_id}|{value}")

            # Update only the matching slot's value
            for key, device_connection_id in device.items():
                if key.endswith("_id") and device_connection_id == connection_id:
                    value_key = key.replace("_id", "_val")
                    device[value_key] = value
                    break
        except Exception:
            _LOGGER.exception("Error updating device value")

    def _generate_hash(self, username, password, salt):
        salt = [ord(c) for c in salt]
        arr1 = "".join(
            chr(salt[i] ^ 92 if i < len(salt) else 92) for i in range(64)
        )
        arr2 = "".join(
            chr(salt[i] ^ 54 if i < len(salt) else 54) for i in range(64)
        )
        hash1 = (
            hashlib.md5((arr2 + username + password).encode())
            .hexdigest()
            .upper()
        )
        return hashlib.md5((arr1 + hash1).encode()).hexdigest().upper()
