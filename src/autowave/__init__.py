"""Public package namespace for the AutoWave driver migration."""

from autowave._version import __version__
from autowave.errors import (
    AutoWaveBusyError,
    AutoWaveChecksumError,
    AutoWaveError,
    AutoWaveNakError,
    AutoWaveNotReadyError,
    AutoWaveProtocolError,
    AutoWaveResponseError,
    AutoWaveValidationError,
)

__all__ = [
    "__version__",
    "AutoWaveBusyError",
    "AutoWaveChecksumError",
    "AutoWaveError",
    "AutoWaveNakError",
    "AutoWaveNotReadyError",
    "AutoWaveProtocolError",
    "AutoWaveResponseError",
    "AutoWaveValidationError",
]
