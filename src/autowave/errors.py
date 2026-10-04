"""AutoWave-specific exception hierarchy.

Concrete errors remain compatible with the shared scpi-driver-core exception
categories while preserving an AutoWave-specific base class for callers that
want to catch every device-driver error from this package.
"""

from __future__ import annotations

from scpi_driver_core.exceptions import ConfigurationError, ProtocolError, ScpiDriverError

__all__ = [
    "AutoWaveBusyError",
    "AutoWaveChecksumError",
    "AutoWaveError",
    "AutoWaveNakError",
    "AutoWaveNotReadyError",
    "AutoWaveProtocolError",
    "AutoWaveResponseError",
    "AutoWaveValidationError",
]


class AutoWaveError(ScpiDriverError):
    """Base class for AutoWave driver errors."""


class AutoWaveValidationError(AutoWaveError, ConfigurationError):
    """Invalid AutoWave command, value, or local protocol configuration."""


class AutoWaveProtocolError(AutoWaveError, ProtocolError):
    """AutoWave wire-protocol violation."""


class AutoWaveResponseError(AutoWaveProtocolError):
    """Malformed, unsupported, or explicitly rejected AutoWave response."""

    def __init__(self, message: str, *, raw: bytes | None = None) -> None:
        super().__init__(message)
        self.raw = raw


class AutoWaveChecksumError(AutoWaveResponseError):
    """Decorated response checksum does not match its payload."""

    def __init__(
        self,
        *,
        expected: int,
        actual: int,
        raw: bytes,
    ) -> None:
        super().__init__(
            f"AutoWave checksum mismatch: expected 0x{expected:02X}, got 0x{actual:02X}",
            raw=raw,
        )
        self.expected = expected
        self.actual = actual


class AutoWaveNakError(AutoWaveResponseError):
    """Instrument returned NAK (0x15)."""


class AutoWaveNotReadyError(AutoWaveResponseError):
    """Instrument returned NOTREADY (0x16)."""


class AutoWaveBusyError(AutoWaveResponseError):
    """Instrument returned BUSY (0x19)."""
