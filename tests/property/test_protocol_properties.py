"""Property tests for AutoWave framing invariants."""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from autowave.errors import AutoWaveChecksumError, AutoWaveResponseError, AutoWaveValidationError
from autowave.protocol import (
    AutoWaveReplyKind,
    calculate_checksum,
    encode_frame,
    parse_reply,
)

_valid_payloads = st.lists(
    st.integers(min_value=0x20, max_value=0xFF),
    min_size=1,
    max_size=256,
).map(bytes).filter(lambda payload: not payload.startswith(b"*"))


@pytest.mark.property
@given(payload=_valid_payloads)
def test_framed_payload_round_trip_preserves_every_byte(payload: bytes) -> None:
    encoded = encode_frame(payload)
    decoded = parse_reply(encoded)

    assert decoded.kind is AutoWaveReplyKind.DATA
    assert decoded.payload == payload
    assert decoded.raw == encoded


@pytest.mark.property
@given(payload=st.binary(min_size=0, max_size=512))
def test_checksum_matches_documented_formula(payload: bytes) -> None:
    masked = sum(payload) & 0xFF
    expected = masked + 0x20 if masked <= 0x20 else masked

    assert calculate_checksum(payload) == expected


@pytest.mark.property
@given(payload=_valid_payloads)
def test_checksum_corruption_is_never_accepted(payload: bytes) -> None:
    corrupted = bytearray(encode_frame(payload))
    corrupted[-1] ^= 0x01

    with pytest.raises(AutoWaveChecksumError):
        parse_reply(bytes(corrupted))


@pytest.mark.property
@given(payload=_valid_payloads)
def test_truncated_decorated_frames_are_never_accepted(payload: bytes) -> None:
    encoded = encode_frame(payload)

    for truncated in (encoded[:-1], encoded[:-2], encoded[1:]):
        with pytest.raises(AutoWaveResponseError):
            parse_reply(truncated)


@pytest.mark.property
@given(control=st.integers(min_value=0x00, max_value=0x1F))
def test_outbound_control_bytes_are_never_accepted(control: int) -> None:
    with pytest.raises(AutoWaveValidationError):
        encode_frame(b"A" + bytes((control,)) + b"B")


@pytest.mark.property
@given(
    payload=st.lists(
        st.integers(min_value=0x20, max_value=0xFF),
        min_size=2,
        max_size=128,
    ).map(bytes)
)
def test_command_size_limit_is_always_enforced(payload: bytes) -> None:
    if payload.startswith(b"*"):
        return
    with pytest.raises(AutoWaveValidationError):
        encode_frame(payload, maximum_size=len(payload) - 1)
