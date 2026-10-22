from __future__ import annotations

import hashlib
from pathlib import Path

from custom_components.gira_homeserver import protocol


def legacy_hash(username: str, password: str, salt: str) -> str:
    """The original implementation from the first version of the integration."""
    codes = [ord(c) for c in salt]
    arr1 = "".join(chr(codes[i] ^ 92 if i < len(codes) else 92) for i in range(64))
    arr2 = "".join(chr(codes[i] ^ 54 if i < len(codes) else 54) for i in range(64))
    inner = hashlib.md5((arr2 + username + password).encode()).hexdigest().upper()
    return hashlib.md5((arr1 + inner).encode()).hexdigest().upper()


def test_hash_matches_legacy() -> None:
    for salt in ("", "abc", "0123456789abcdef", "x" * 80):
        assert protocol.generate_hash("user", "pw", salt) == legacy_hash("user", "pw", salt)


def test_frames_split_across_chunks() -> None:
    buffer = protocol.FrameBuffer()
    assert buffer.feed(b"1|10|1.0|0\x001|11") == [protocol.Frame(1, ("10", "1.0", "0"))]
    frames = buffer.feed(b"|0.0|0\x00100|\x00")
    assert frames == [protocol.Frame(1, ("11", "0.0", "0")), protocol.Frame(100, ("",))]


def test_updates_group_triples_and_drop_partial_tail() -> None:
    frame = protocol.decode_frame("2|1|a|0|2|b|0|")
    assert frame is not None
    assert frame.updates() == [protocol.Update("1", "a", "0"), protocol.Update("2", "b", "0")]


def test_garbage_action_is_ignored() -> None:
    assert protocol.decode_frame("HTTP/1.1 200 OK") is None
    assert protocol.FrameBuffer().feed(b"nonsense\x00") == []


def test_real_state_dump_survives_any_chunking() -> None:
    raw = (Path(__file__).parent / "fixtures" / "state_dump.bin").read_bytes()
    for size in (1, 7, 512, len(raw)):
        buffer = protocol.FrameBuffer()
        frames = [f for i in range(0, len(raw), size) for f in buffer.feed(raw[i : i + size])]
        assert len(frames) == 186
        assert frames[-1] == protocol.Frame(protocol.ACTION_STATE_END, ("", ""))
        updates = [u for f in frames if f.action == protocol.ACTION_STATE for u in f.updates()]
        assert len(updates) == 183
        assert all(u.flag == "0" for u in updates)
