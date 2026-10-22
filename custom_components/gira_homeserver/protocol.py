"""Wire format of the HomeServer client protocol."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

LOGIN_REQUEST = "GET /QUAD/LOGIN \r\n\r\n"
REQUEST_STATE = "94||"

ACTION_SET = 1
ACTION_STATE = 2
ACTION_STATE_END = 95
ACTION_SALT = 91
ACTION_LOGIN_OK = 93
ACTION_USER_REQUEST = 100

_TERMINATOR = "\x00"


@dataclass(frozen=True, slots=True)
class Update:
    tag: str
    value: str
    flag: str


@dataclass(frozen=True, slots=True)
class Frame:
    action: int
    fields: tuple[str, ...]

    def updates(self) -> list[Update]:
        """Group the fields into (tag, value, flag) triples, dropping a partial tail."""
        f = self.fields
        return [Update(*f[i : i + 3]) for i in range(0, len(f) - 2, 3)]


def decode_frame(raw: str) -> Frame | None:
    """Parse one frame. Returns None when the action is not a number."""
    action, *fields = raw.split("|")
    try:
        return Frame(int(action), tuple(fields))
    except ValueError:
        return None


class FrameBuffer:
    """Reassembles NUL terminated frames from an arbitrary chunked byte stream."""

    def __init__(self) -> None:
        self._pending = ""

    def feed(self, data: bytes) -> list[Frame]:
        self._pending += data.decode(errors="replace")
        *complete, self._pending = self._pending.split(_TERMINATOR)
        return [frame for raw in complete if raw and (frame := decode_frame(raw))]


def encode(message: str) -> bytes:
    return (message + _TERMINATOR).encode()


def login_user(username: str) -> str:
    return f"90|{username}|"


def login_hash(digest: str) -> str:
    return f"92|{digest}|"


def set_value(tag: str, value: str) -> str:
    return f"{ACTION_SET}|{tag}|{value}"


def generate_hash(username: str, password: str, salt: str) -> str:
    """Salted MD5 construction taken from the official app (HMAC-like, not standard)."""
    salt_bytes = salt.encode()
    outer = bytes((salt_bytes[i] if i < len(salt_bytes) else 0) ^ 0x5C for i in range(64))
    inner = bytes((salt_bytes[i] if i < len(salt_bytes) else 0) ^ 0x36 for i in range(64))
    first = hashlib.md5(inner + username.encode() + password.encode()).hexdigest().upper()
    return hashlib.md5(outer + first.encode()).hexdigest().upper()
