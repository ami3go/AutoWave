"""Unit tests for the transport-free AutoWave protocol layer."""

from __future__ import annotations

import pytest
from scpi_driver_core.exceptions import ConfigurationError, ProtocolError, ScpiDriverError

from autowave.errors import (
    AutoWaveBusyError,
    AutoWaveChecksumError,
    AutoWaveError,
    AutoWaveNakError,
    AutoWaveNotReadyError,
    AutoWaveResponseError,
    AutoWaveValidationError,
)
from autowave.protocol import (
    ACK,
    BUSY,
    ETX,
    NAK,
    NOT_READY,
    STX,
    AutoWaveReplyKind,
    calculate_checksum,
    decode_payload_text,
    encode_command,
    encode_frame,
    parse_reply,
    raise_for_status,
)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"STAT? PSRC", 0xD3),
        (b"LCN?", 0x3C),
        (b" ", 0x40),
    ],
)
def test_documented_checksum_vectors(payload: bytes, expected: int) -> None:
    assert calculate_checksum(payload) == expected


def test_encode_command_matches_manual_vector() -> None:
    assert encode_command("STAT? PSRC") == b"\x02STAT? PSRC\x03\xd3"


def test_encode_frame_preserves_extended_single_byte_payload() -> None:
    payload = bytes((0x41, 0x80, 0xFF))
    frame = encode_frame(payload)
    assert frame[0] == STX
    assert frame[1:-2] == payload
    assert frame[-2] == ETX


@pytest.mark.parametrize("command", ["", "*IDN?", "*GTL", "LINE\nBREAK", "CR\rBREAK"])
def test_invalid_string_commands_are_rejected(command: str) -> None:
    with pytest.raises(AutoWaveValidationError):
        encode_command(command)


def test_non_ascii_string_command_is_rejected_without_guessing_vendor_code_page() -> None:
    with pytest.raises(AutoWaveValidationError, match="ASCII"):
        encode_command("DISP café")


def test_empty_raw_command_payload_is_rejected() -> None:
    with pytest.raises(AutoWaveValidationError, match="must not be empty"):
        encode_frame(b"")


def test_control_byte_in_raw_command_is_rejected() -> None:
    with pytest.raises(AutoWaveValidationError, match="control byte"):
        encode_frame(b"ABC\x1fDEF")


def test_non_string_command_is_rejected() -> None:
    with pytest.raises(AutoWaveValidationError, match="command must be str"):
        encode_command(b"STAT? TEST")  # type: ignore[arg-type]


def test_command_payload_limit_is_enforced() -> None:
    with pytest.raises(AutoWaveValidationError, match="exceeds"):
        encode_frame(b"A" * 5, maximum_size=4)


@pytest.mark.parametrize(
    ("raw", "kind"),
    [
        (bytes((ACK,)), AutoWaveReplyKind.ACK),
        (bytes((NAK,)), AutoWaveReplyKind.NAK),
        (bytes((NOT_READY,)), AutoWaveReplyKind.NOT_READY),
        (bytes((BUSY,)), AutoWaveReplyKind.BUSY),
    ],
)
def test_simple_replies_are_classified(raw: bytes, kind: AutoWaveReplyKind) -> None:
    reply = parse_reply(raw)
    assert reply.kind is kind
    assert reply.raw == raw
    assert reply.payload is None


def test_unknown_one_byte_reply_is_rejected() -> None:
    with pytest.raises(AutoWaveResponseError, match="unknown one-byte"):
        parse_reply(b"X")


def test_decorated_reply_round_trip() -> None:
    raw = encode_frame(b"STAT TEST:8,8,8,8,4,4,0")
    reply = parse_reply(raw)

    assert reply.kind is AutoWaveReplyKind.DATA
    assert reply.raw == raw
    assert reply.payload == b"STAT TEST:8,8,8,8,4,4,0"
    assert decode_payload_text(reply) == "STAT TEST:8,8,8,8,4,4,0"


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"\x02",
        b"\x02A",
        b"A\x03\x41",
        b"\x02A\x04\x41",
    ],
)
def test_malformed_decorated_replies_are_rejected(raw: bytes) -> None:
    with pytest.raises(AutoWaveResponseError):
        parse_reply(raw)


def test_control_byte_in_decorated_response_is_rejected() -> None:
    payload = b"A\x1fB"
    raw = bytes((STX,)) + payload + bytes((ETX, calculate_checksum(payload)))

    with pytest.raises(AutoWaveResponseError, match="control byte"):
        parse_reply(raw)


def test_bad_checksum_reports_expected_and_actual_values() -> None:
    valid = bytearray(encode_frame(b"LCN?"))
    valid[-1] ^= 0x01

    with pytest.raises(AutoWaveChecksumError) as caught:
        parse_reply(bytes(valid))

    assert caught.value.expected == 0x3C
    assert caught.value.actual == 0x3D
    assert caught.value.raw == bytes(valid)


def test_response_size_limit_is_enforced_before_parsing() -> None:
    raw = encode_frame(b"ABCDE")
    with pytest.raises(AutoWaveResponseError, match="exceeds"):
        parse_reply(raw, maximum_size=len(raw) - 1)


def test_decorated_non_ascii_payload_is_preserved_but_not_text_decoded() -> None:
    raw = encode_frame(bytes((0x41, 0x80, 0xFF)))
    reply = parse_reply(raw)

    assert reply.payload == bytes((0x41, 0x80, 0xFF))
    with pytest.raises(AutoWaveResponseError, match="non-ASCII"):
        decode_payload_text(reply)


def test_decode_payload_text_rejects_status_reply() -> None:
    reply = parse_reply(bytes((ACK,)))
    with pytest.raises(AutoWaveResponseError, match="no decorated text payload"):
        decode_payload_text(reply)


@pytest.mark.parametrize(
    ("raw", "exception_type"),
    [
        (bytes((NAK,)), AutoWaveNakError),
        (bytes((NOT_READY,)), AutoWaveNotReadyError),
        (bytes((BUSY,)), AutoWaveBusyError),
    ],
)
def test_raise_for_status_uses_typed_errors(
    raw: bytes,
    exception_type: type[AutoWaveResponseError],
) -> None:
    reply = parse_reply(raw)
    with pytest.raises(exception_type) as caught:
        raise_for_status(reply)
    assert caught.value.raw == raw


@pytest.mark.parametrize("raw", [bytes((ACK,)), encode_frame(b"OK")])
def test_raise_for_status_accepts_ack_and_data(raw: bytes) -> None:
    reply = parse_reply(raw)
    assert raise_for_status(reply) is reply


def test_error_hierarchy_integrates_with_scpi_driver_core() -> None:
    assert issubclass(AutoWaveError, ScpiDriverError)
    assert issubclass(AutoWaveValidationError, ConfigurationError)
    assert issubclass(AutoWaveResponseError, ProtocolError)


@pytest.mark.parametrize("bad_limit", [0, -1, True, 1.5])
def test_invalid_limits_are_rejected(bad_limit: object) -> None:
    with pytest.raises(AutoWaveValidationError):
        encode_frame(b"A", maximum_size=bad_limit)  # type: ignore[arg-type]
    with pytest.raises(AutoWaveValidationError):
        parse_reply(b"\x06", maximum_size=bad_limit)  # type: ignore[arg-type]


def test_bytes_are_required_at_raw_protocol_boundary() -> None:
    with pytest.raises(AutoWaveValidationError):
        calculate_checksum(bytearray(b"ABC"))  # type: ignore[arg-type]
    with pytest.raises(AutoWaveValidationError):
        encode_frame(bytearray(b"ABC"))  # type: ignore[arg-type]
    with pytest.raises(AutoWaveValidationError):
        parse_reply(bytearray(b"\x06"))  # type: ignore[arg-type]
