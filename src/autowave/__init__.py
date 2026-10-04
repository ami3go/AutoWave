"""Public package namespace for the AutoWave driver migration."""

from autowave._version import __version__
from autowave.connection import (
    AutoWaveConnection,
    discover_autowave_resources,
    parse_autowave_identity,
    require_single_autowave,
)
from autowave.driver import DEFAULT_SAFE_QUERY_RETRY_POLICY, AutoWave
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
from autowave.models import (
    AutoWaveIdentity,
    BusyPolicy,
    DirectoryKind,
    DiscoveredAutoWave,
    GeneratorMode,
    TestStatus,
    TriggerMode,
)

__all__ = [
    "__version__",
    "DEFAULT_SAFE_QUERY_RETRY_POLICY",
    "AutoWave",
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
    "DirectoryKind",
    "DiscoveredAutoWave",
    "GeneratorMode",
    "TestStatus",
    "TriggerMode",
    "discover_autowave_resources",
    "parse_autowave_identity",
    "require_single_autowave",
]
