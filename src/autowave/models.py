"""Typed AutoWave value models and bounded policy values."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, IntEnum

from autowave.errors import AutoWaveValidationError

__all__ = [
    "DEFAULT_BUSY_POLICY",
    "AutoWaveIdentity",
    "BusyPolicy",
    "DirectoryKind",
    "DiscoveredAutoWave",
    "GeneratorMode",
    "TestStatus",
    "TriggerMode",
]


class GeneratorMode(Enum):
    """Documented AutoWave operating modes used by the legacy driver."""

    GENERATOR = "GEN"
    RECORDER = "REC"
    GENERATOR_RECORDER = "GNRC"


class TriggerMode(IntEnum):
    """Generator trigger modes documented by AutoWave."""

    OFF = 0
    MANUAL_START = 1
    TRIGGER_INPUT_START = 2
    AUTO = 3
    MANUAL_EVENT = 4
    TRIGGER_INPUT_EVENT = 5
    MANUAL_ITERATION = 6
    TRIGGER_INPUT_ITERATION = 7


class DirectoryKind(Enum):
    """Named AutoWave application directories."""

    DOWNLOAD = "DOWD"
    RECORD = "RECD"
    UPGRADE = "UPGD"
    LOG = "LOGD"


@dataclass(frozen=True, slots=True)
class AutoWaveIdentity:
    """Normalized AutoWave identification while preserving the exact raw reply."""

    manufacturer: str
    model: str
    serial_number: str | None
    firmware_version: str | None
    outputs: int | None
    inputs: int | None
    raw: str


@dataclass(frozen=True, slots=True)
class DiscoveredAutoWave:
    """One AutoWave found during explicitly requested VISA discovery."""

    resource_name: str
    identity: AutoWaveIdentity


@dataclass(frozen=True, slots=True)
class TestStatus:
    """Typed form of the seven-value STAT? TEST response."""

    test_state: int
    output_states: tuple[int, int, int, int]
    input_states: tuple[int, int]
    raw: str


@dataclass(frozen=True, slots=True)
class BusyPolicy:
    """Bounds for the vendor-defined exact-message BUSY re-query loop."""

    attempts: int = 10
    max_elapsed_s: float = 5.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.attempts, bool)
            or not isinstance(self.attempts, int)
            or self.attempts < 1
        ):
            raise AutoWaveValidationError(
                f"BUSY attempts must be a positive integer, got {self.attempts!r}"
            )
        if not math.isfinite(self.max_elapsed_s) or self.max_elapsed_s <= 0:
            raise AutoWaveValidationError(
                f"BUSY max_elapsed_s must be finite and positive, got {self.max_elapsed_s!r}"
            )


DEFAULT_BUSY_POLICY = BusyPolicy()
