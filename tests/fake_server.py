"""In-process HomeServer that speaks enough of the protocol for tests."""

from __future__ import annotations

import asyncio
import contextlib

from custom_components.gira_homeserver import protocol

TOKEN = "tok123"
SALT = "salt1234"


class FakeHomeServer:
    def __init__(self, project: bytes, username: str = "user", password: str = "secret") -> None:
        self.project = project
        self.username = username
        self.password = password
        self.states: dict[str, str] = {}
        self.commands: list[tuple[str, str]] = []
        self.logins = 0
        self._server: asyncio.Server | None = None
        self._writers: list[asyncio.StreamWriter] = []
        self.port = 0

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        await self.drop_clients()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def drop_clients(self) -> None:
        for writer in self._writers:
            writer.close()
        self._writers.clear()

    def push(self, tag: str, value: str) -> None:
        self.states[tag] = value
        for writer in self._writers:
            writer.write(f"1|{tag}|{value}|0\x00".encode())

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            if request.startswith(b"GET /QUAD/LOGIN"):
                await self._session(reader, writer)
            else:
                body = self.project
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Type: text/xml\r\n"
                    + f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
                    + body
                )
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            with contextlib.suppress(ConnectionError):
                await writer.wait_closed()

    async def _frame(self, reader: asyncio.StreamReader) -> str:
        while not (frame := (await reader.readuntil(b"\x00")).decode().rstrip("\x00")):
            pass
        return frame

    async def _session(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writer.write(b"100||\x00")
        user = (await self._frame(reader)).split("|")[1]
        writer.write(f"91|{SALT}||\x00".encode())
        digest = (await self._frame(reader)).split("|")[1]
        self.logins += 1
        expected = protocol.generate_hash(self.username, self.password, SALT)
        if user != self.username or digest != expected:
            return
        writer.write(f"93|{TOKEN}|\x00".encode())
        self._writers.append(writer)
        while True:
            frame = await self._frame(reader)
            if frame.startswith("94"):
                for tag, value in self.states.items():
                    writer.write(f"2|{tag}|{value}|0\x00".encode())
                writer.write(b"95||\x00")
            elif frame.startswith("1|"):
                _, tag, value = frame.split("|")[:3]
                self.commands.append((tag, value))
                self.push(tag, value)
