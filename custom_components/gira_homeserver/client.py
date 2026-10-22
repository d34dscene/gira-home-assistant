"""Connection to the Gira HomeServer."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import defaultdict
from collections.abc import Callable, Iterable

import aiohttp
from homeassistant.exceptions import HomeAssistantError

from . import protocol

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10
RECONNECT_MIN = 5
RECONNECT_MAX = 120

type Listener = Callable[[], None]


class GiraError(HomeAssistantError):
    """Base error."""


class GiraConnectionError(GiraError):
    """The HomeServer could not be reached or the link dropped."""


class GiraAuthError(GiraError):
    """The HomeServer rejected the login."""


class GiraClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self.host = host
        self.port = port
        self._username = username
        self._password = password
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._buffer = protocol.FrameBuffer()
        self._token = ""
        self._values: dict[str, str] = {}
        self._tag_listeners: defaultdict[str, list[Listener]] = defaultdict(list)
        self._availability_listeners: list[Listener] = []
        self._write_lock = asyncio.Lock()
        self._state_seen = asyncio.Event()
        self._closing = False
        self._hash_sent = False
        self.available = False

    def value(self, tag: str | None) -> str | None:
        return self._values.get(tag) if tag else None

    def subscribe(self, tags: Iterable[str], listener: Listener) -> Listener:
        """Call listener when any of the tags changes. Returns the unsubscribe function."""
        tags = tuple(tags)
        for tag in tags:
            self._tag_listeners[tag].append(listener)

        def unsubscribe() -> None:
            for tag in tags:
                self._tag_listeners[tag].remove(listener)

        return unsubscribe

    def subscribe_availability(self, listener: Listener) -> Listener:
        self._availability_listeners.append(listener)
        return lambda: self._availability_listeners.remove(listener)

    async def connect(self) -> None:
        """Open the link and log in once. Never retries."""
        self._buffer = protocol.FrameBuffer()
        self._hash_sent = False
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT):
                self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
                await self._login()
                await self._send(protocol.REQUEST_STATE)
        except (OSError, TimeoutError) as err:
            await self._close_socket()
            if self._hash_sent and isinstance(err, TimeoutError):
                raise GiraAuthError("No login confirmation from the HomeServer") from err
            raise GiraConnectionError(f"Cannot connect to {self.host}:{self.port}") from err
        except GiraError:
            await self._close_socket()
            raise
        self._set_available(True)

    async def disconnect(self) -> None:
        self._closing = True
        await self._close_socket()
        self._set_available(False)

    async def fetch_project(self) -> bytes:
        url = f"http://{self.host}:{self.port}/quad/client/client_project.xml?{self._token}"
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                return await resp.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise GiraConnectionError("Cannot download the project") from err

    async def wait_for_state(self, seconds: float) -> bool:
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout(seconds):
                await self._state_seen.wait()
        return self._state_seen.is_set()

    async def set_value(self, tag: str, value: str) -> None:
        if not self.available:
            raise GiraConnectionError("Not connected to the HomeServer")
        await self._send(protocol.set_value(tag, value))

    async def run(self) -> None:
        """Process pushed updates and reconnect when the link drops. Raises on auth errors."""
        delay = RECONNECT_MIN
        while not self._closing:
            try:
                await self._read_loop()
            except (OSError, GiraConnectionError) as err:
                if self._closing:
                    return
                _LOGGER.warning("Connection to the HomeServer lost: %s", err)
            self._set_available(False)
            await self._close_socket()
            while not self._closing:
                await asyncio.sleep(delay)
                if self._closing:
                    return
                try:
                    await self.connect()
                except GiraAuthError:
                    _LOGGER.error("HomeServer rejected the login, not retrying")
                    raise
                except GiraConnectionError:
                    delay = min(delay * 2, RECONNECT_MAX)
                    continue
                delay = RECONNECT_MIN
                break

    async def _read_loop(self) -> None:
        while True:
            for frame in await self._read_frames():
                if frame.action in (protocol.ACTION_SET, protocol.ACTION_STATE):
                    self._apply(frame.updates())
                elif frame.action == protocol.ACTION_STATE_END:
                    self._state_seen.set()

    async def _read_frames(self) -> list[protocol.Frame]:
        if not self._reader:
            raise GiraConnectionError("Not connected")
        data = await self._reader.read(4096)
        if not data:
            raise GiraConnectionError("Connection closed by the HomeServer")
        return self._buffer.feed(data)

    def _apply(self, updates: list[protocol.Update]) -> None:
        notify: list[Listener] = []
        for update in updates:
            self._values[update.tag] = update.value
            notify.extend(self._tag_listeners.get(update.tag, ()))
        for listener in dict.fromkeys(notify):
            listener()

    async def _login(self) -> None:
        await self._send(protocol.LOGIN_REQUEST)
        while True:
            try:
                frames = await self._read_frames()
            except GiraConnectionError as err:
                if self._hash_sent:
                    raise GiraAuthError("Login rejected") from err
                raise
            for frame in frames:
                match frame.action:
                    case protocol.ACTION_USER_REQUEST:
                        await self._send(protocol.login_user(self._username))
                    case protocol.ACTION_SALT:
                        digest = protocol.generate_hash(
                            self._username, self._password, frame.fields[0]
                        )
                        await self._send(protocol.login_hash(digest))
                        self._hash_sent = True
                    case protocol.ACTION_LOGIN_OK:
                        self._token = frame.fields[0]
                        return
                    case _:
                        _LOGGER.debug("Ignoring frame during login: %s", frame.action)

    async def _send(self, message: str) -> None:
        if not self._writer:
            raise GiraConnectionError("Not connected")
        data = protocol.encode(message)
        async with self._write_lock:
            try:
                self._writer.write(data)
                await self._writer.drain()
            except OSError as err:
                raise GiraConnectionError("Failed to send") from err

    async def _close_socket(self) -> None:
        writer, self._writer, self._reader = self._writer, None, None
        if writer:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

    def _set_available(self, available: bool) -> None:
        if self.available == available:
            return
        self.available = available
        for listener in list(self._availability_listeners):
            listener()
