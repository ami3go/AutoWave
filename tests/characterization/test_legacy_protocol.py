"""Protocol characterization for the legacy AutoWave implementation.

These tests intentionally freeze both correct legacy behavior and known defects.
They are not the target architecture; later migration PRs may replace the legacy
module while preserving the verified protocol vectors in equivalent tests.
"""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("STAT? PSRC", 0xD3),
        ("LCN?", 0x3C),
        (" ", 0x40),  # raw checksum 0x20 must be adjusted by +0x20
    ],
)
def test_legacy_checksum_vectors(legacy_module, command: str, expected: int) -> None:
    assert legacy_module.str2check_sum(command) == expected


def test_legacy_frame_bytes_match_verified_manual_vector(
    legacy_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    writes: list[bytes] = []

    class Instrument:
        def write_raw(self, data: bytes) -> int:
            writes.append(data)
            return len(data)

    interface = legacy_module.com_interface.__new__(legacy_module.com_interface)
    interface.inst = Instrument()
    monkeypatch.setattr(legacy_module, "delay", lambda *_args, **_kwargs: None)

    interface.psend("STAT? PSRC")

    assert writes == [b"\x02STAT? PSRC\x03\xd3"]


def test_legacy_decorated_response_round_trip(
    legacy_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    writes: list[bytes] = []

    class Instrument:
        def write_raw(self, data: bytes) -> int:
            writes.append(data)
            return len(data)

        def read_raw(self) -> bytes:
            return b"\x02TRIG:GEN 1\x03\x9b"

    interface = legacy_module.com_interface.__new__(legacy_module.com_interface)
    interface.inst = Instrument()
    monkeypatch.setattr(legacy_module, "delay", lambda *_args, **_kwargs: None)

    assert interface.pquery("TRIG:GEN 1") == "TRIG:GEN 1"
    assert writes == [b"\x02TRIG:GEN 1\x03\x9b"]


@pytest.mark.parametrize("reply", [b"\x06", b"\x15", b"\x16", b"\x19"])
def test_legacy_simple_protocol_replies_are_not_completed_cleanly(
    legacy_module,
    monkeypatch: pytest.MonkeyPatch,
    reply: bytes,
) -> None:
    """Legacy pquery retries all simple responses and eventually falls through.

    ACK (0x06), NAK (0x15), NOTREADY (0x16), and BUSY (0x19) all need explicit
    typed handling in the migrated protocol layer.
    """

    class Instrument:
        writes = 0

        def write_raw(self, data: bytes) -> int:
            self.writes += 1
            return len(data)

        def read_raw(self) -> bytes:
            return reply

    instrument = Instrument()
    interface = legacy_module.com_interface.__new__(legacy_module.com_interface)
    interface.inst = instrument
    monkeypatch.setattr(legacy_module, "delay", lambda *_args, **_kwargs: None)

    assert interface.pquery("STAT? TEST") is None
    assert instrument.writes == 10


def test_legacy_query_exception_masks_original_failure(
    legacy_module, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Instrument:
        def query(self, _command: str) -> str:
            raise RuntimeError("primary VISA failure")

    interface = legacy_module.com_interface.__new__(legacy_module.com_interface)
    interface.inst = Instrument()
    monkeypatch.setattr(legacy_module, "delay", lambda *_args, **_kwargs: None)

    with pytest.raises(UnboundLocalError):
        interface.query("*IDN?")


def test_legacy_range_check_silently_clamps(legacy_module) -> None:
    assert legacy_module.range_check(75, 0, 60, "voltage") == 60
    assert legacy_module.range_check(-1, 0, 60, "voltage") == 0
