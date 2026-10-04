"""Public package namespace for the AutoWave driver migration."""

from autowave._version import __version__
from autowave.connection import (
    AutoWaveConnection,
    discover_autowave_resources,
    parse_autowave_identity,
    require_single_autowave,
)
from autowave.errors import (
    AutoWaveBusyError,
    AutoWaveChecksumError,
    AutoWaveConnectionStateError,
    AutoWaveDiscoveryError,
    AutoWaveError,
    AutoWaveIdentityError,
    AutoWaveNakError,
    AutoWaveNotReadyError,
    AutoWaveProtocolError,
    AutoWaveResponseError,
    AutoWaveValidationError,
)
from autowave.models import AutoWaveIdentity, BusyPolicy, DiscoveredAutoWave

__all__ = [
    "__version__",
    "AutoWaveBusyError",
    "AutoWaveChecksumError",
    "AutoWaveConnection",
    "AutoWaveConnectionStateError",
    "AutoWaveDiscoveryError",
    "AutoWaveError",
    "AutoWaveIdentity",
    "AutoWaveIdentityError",
    "AutoWaveNakError",
    "AutoWaveNotReadyError",
    "AutoWaveProtocolError",
    "AutoWaveResponseError",
    "AutoWaveValidationError",
    "BusyPolicy",
    "DiscoveredAutoWave",
    "discover_autowave_resources",
    "parse_autowave_identity",
    "require_single_autowave",
]
