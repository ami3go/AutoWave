"""Pure AutoWave framing and reply parsing.

This module contains no transport or session I/O.  It converts validated
AutoWave payloads to/from the vendor STX/ETX/checksum envelope and classifies
the four documented single-byte protocol replies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from autowave.errors import (
    AutoWaveBusyError,
    AutoWaveChecksumError,
    AutoWaveNakError,
    AutoWaveNotReadyError,
    AutoWaveResponseError,
    AutoWaveValidationError,
)

__all__ = [
    "ACK",
    "BUSY",
    "DEFAULT_MAX_COMMAND_PAYLOAD",
    "DEFAULT_MAX_RESPONSE_SIZE",
    "ETX",
    "NAK",
    "NOT_READY",
    "STX",
    "AutoWaveReply",
    "AutoWaveReplyKind",
    "calculate_checksum",
    "decode_payload_text",
    "encode_command",
    "encode_frame",
    "parse_reply",
    "raise_for_status",
]

STX: Final = 0x02
ETX: Final = 0x03
ACK: Final = 0x06
NAK: Final = 0x15
NOT_READY: Final = 0x16
BUSY: Final = 0x19

DEFAULT_MAX_COMMAND_PAYLOAD: Final = 4096
DEFAULT_MAX_RESPONSE_SIZE: Final = 65536


class AutoWaveReplyKind(Enum):
    """Classification of one complete AutoWave protocol response."""

    ACK = "ack"
    NAK = "nak"
    NOT_READY = "not_ready"
    BUSY = "busy"
    DATA = "data"


@dataclass(frozen=True, slots=True)
class AutoWaveReply:
    """Parsed response preserving both semantic kind and exact wire bytes."""

    kind: AutoWaveReplyKind
    raw: bytes
    payload: bytes | None = None


_SIMPLE_REPLIES: Final = {
    ACK: AutoWaveReplyKind.ACK,
    NAK: AutoWaveReplyKind.NAK,
    NOT_READY: AutoWaveReplyKind.NOT_READY,
    BUSY: AutoWaveReplyKind.BUSY,
}


def _validate_positive_limit(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AutoWaveValidationError(f"{name} must be a positive integer, got {value!r}")


def _validate_command_payload(payload: bytes, *, maximum_size: int) -> None:
    if not isinstance(payload, bytes):
        raise AutoWaveValidationError(
            f"command payload must be bytes, got {type(payload).__name__}"
        )
    _validate_positive_limit(maximum_size, "maximum_size")
    if not payload:
        raise AutoWaveValidationError("command payload must not be empty")
    if len(payload) > maximum_size:
        raise AutoWaveValidationError(
            f"command payload of {len(payload)} bytes exceeds maximum_size {maximum_size}"
        )
    if payload.startswith(b"*"):
        raise AutoWaveValidationError("commands beginning with '*' are always unframed on AutoWave")
    control = next((value for value in payload if value < 0x20), None)
    if control is not None:
        raise AutoWaveValidationError(
            f"command payload contains unsupported control byte 0x{control:02X}"
        )


def calculate_checksum(payload: bytes) -> int:
    """Return the documented AutoWave one-byte checksum for payload bytes."""

    if not isinstance(payload, bytes):
        raise AutoWaveValidationError(
            f"checksum payload must be bytes, got {type(payload).__name__}"
        )
    value = sum(payload) & 0xFF
    if value <= 0x20:
        value += 0x20
    return value


def encode_frame(
    payload: bytes,
    *,
    maximum_size: int = DEFAULT_MAX_COMMAND_PAYLOAD,
) -> bytes:
    """Wrap one validated non-star command payload in the AutoWave envelope."""

    _validate_command_payload(payload, maximum_size=maximum_size)
    return bytes((STX,)) + payload + bytes((ETX, calculate_checksum(payload)))


def encode_command(
    command: str,
    *,
    maximum_size: int = DEFAULT_MAX_COMMAND_PAYLOAD,
) -> bytes:
    """ASCII-encode and frame one non-star AutoWave command."""

    if not isinstance(command, str):
        raise AutoWaveValidationError(f"command must be str, got {type(command).__name__}")
    if not command:
        raise AutoWaveValidationError("command must not be empty")
    try:
        payload = command.encode("ascii", errors="strict")
    except UnicodeEncodeError as exc:
        raise AutoWaveValidationError(
            "string commands are limited to ASCII until the vendor 0x80-0xFF code page is verified"
        ) from exc
    return encode_frame(payload, maximum_size=maximum_size)


def parse_reply(
    data: bytes,
    *,
    maximum_size: int = DEFAULT_MAX_RESPONSE_SIZE,
) -> AutoWaveReply:
    """Parse one complete backend-delimited AutoWave response message."""

    if not isinstance(data, bytes):
        raise AutoWaveValidationError(f"response must be bytes, got {type(data).__name__}")
    _validate_positive_limit(maximum_size, "maximum_size")
    if not data:
        raise AutoWaveResponseError("AutoWave response is empty", raw=data)
    if len(data) > maximum_size:
        raise AutoWaveResponseError(
            f"AutoWave response of {len(data)} bytes exceeds maximum_size {maximum_size}",
            raw=data,
        )

    if len(data) == 1:
        kind = _SIMPLE_REPLIES.get(data[0])
        if kind is None:
            raise AutoWaveResponseError(
                f"unknown one-byte AutoWave response 0x{data[0]:02X}",
                raw=data,
            )
        return AutoWaveReply(kind=kind, raw=data)

    if len(data) < 4:
        raise AutoWaveResponseError(
            f"decorated AutoWave response is too short: {len(data)} bytes",
            raw=data,
        )
    if data[0] != STX:
        raise AutoWaveResponseError(
            f"decorated AutoWave response does not start with STX 0x{STX:02X}",
            raw=data,
        )
    if data[-2] != ETX:
        raise AutoWaveResponseError(
            f"decorated AutoWave response does not end with ETX 0x{ETX:02X} before checksum",
            raw=data,
        )

    payload = data[1:-2]
    control = next((value for value in payload if value < 0x20), None)
    if control is not None:
        raise AutoWaveResponseError(
            f"decorated AutoWave response contains unsupported control byte 0x{control:02X}",
            raw=data,
        )

    expected = calculate_checksum(payload)
    actual = data[-1]
    if actual != expected:
        raise AutoWaveChecksumError(expected=expected, actual=actual, raw=data)

    return AutoWaveReply(kind=AutoWaveReplyKind.DATA, raw=data, payload=payload)


def decode_payload_text(reply: AutoWaveReply) -> str:
    """Decode a decorated data reply as ASCII without altering its content."""

    if reply.kind is not AutoWaveReplyKind.DATA or reply.payload is None:
        raise AutoWaveResponseError(
            f"AutoWave {reply.kind.value} reply has no decorated text payload",
            raw=reply.raw,
        )
    try:
        return reply.payload.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise AutoWaveResponseError(
            "AutoWave response contains non-ASCII bytes; vendor code page is not verified",
            raw=reply.raw,
        ) from exc


def raise_for_status(reply: AutoWaveReply) -> AutoWaveReply:
    """Raise a typed exception for explicit negative/transient protocol statuses."""

    if reply.kind is AutoWaveReplyKind.NAK:
        raise AutoWaveNakError("AutoWave returned NAK (0x15)", raw=reply.raw)
    if reply.kind is AutoWaveReplyKind.NOT_READY:
        raise AutoWaveNotReadyError("AutoWave returned NOTREADY (0x16)", raw=reply.raw)
    if reply.kind is AutoWaveReplyKind.BUSY:
        raise AutoWaveBusyError("AutoWave returned BUSY (0x19)", raw=reply.raw)
    return reply
