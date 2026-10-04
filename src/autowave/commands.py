"""Pure AutoWave command construction.

All functions return one command only and reject embedded CR/LF so callers
cannot accidentally inject a second instrument operation.
"""

from __future__ import annotations

import math
from autowave.errors import AutoWaveValidationError
from autowave.models import DirectoryKind, GeneratorMode, TriggerMode

__all__ = [
    "MAX_OUTPUT_CHANNEL",
    "OFFSET_MAX_V",
    "OFFSET_MIN_V",
    "VOLTAGE_MAX_V",
    "VOLTAGE_MIN_V",
    "directory_query",
    "file_details_query",
    "file_duration_query",
    "file_exists_query",
    "list_directory",
    "select_file",
    "set_generator_mode",
    "set_offset",
    "set_trigger_mode",
    "set_voltage",
    "status_input_query",
    "status_mac_query",
    "status_output_query",
    "status_system_query",
    "status_test_query",
]

MAX_OUTPUT_CHANNEL = 4
VOLTAGE_MIN_V = 0.0
VOLTAGE_MAX_V = 60.0
OFFSET_MIN_V = -60.0
OFFSET_MAX_V = 60.0


def _text_argument(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise AutoWaveValidationError(f"{name} must be str, got {type(value).__name__}")
    if not value:
        raise AutoWaveValidationError(f"{name} must not be empty")
    if "\r" in value or "\n" in value:
        raise AutoWaveValidationError(f"{name} must not contain CR or LF")
    if ";" in value:
        raise AutoWaveValidationError(f"{name} must not contain a command separator ';'")
    return value


def _channel(channel: int, *, maximum: int = MAX_OUTPUT_CHANNEL) -> int:
    if isinstance(channel, bool) or not isinstance(channel, int):
        raise AutoWaveValidationError(f"channel must be an integer, got {channel!r}")
    if not 1 <= channel <= maximum:
        raise AutoWaveValidationError(f"channel must be in range 1..{maximum}, got {channel}")
    return channel


def _number(
    value: int | float,
    *,
    name: str,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AutoWaveValidationError(f"{name} must be a real number, got {value!r}")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise AutoWaveValidationError(f"{name} must be finite, got {value!r}")
    if not minimum <= numeric <= maximum:
        raise AutoWaveValidationError(
            f"{name} must be in range {minimum:g}..{maximum:g}, got {numeric:g}"
        )
    return numeric


def _format_number(value: float) -> str:
    if value == 0:
        return "0"
    return format(value, ".15g")


def set_generator_mode(mode: GeneratorMode) -> str:
    if not isinstance(mode, GeneratorMode):
        raise AutoWaveValidationError(f"mode must be GeneratorMode, got {type(mode).__name__}")
    return f"MOD {mode.value}"


def set_trigger_mode(mode: TriggerMode) -> str:
    if not isinstance(mode, TriggerMode):
        raise AutoWaveValidationError(f"mode must be TriggerMode, got {type(mode).__name__}")
    return f"TRIG:GEN {int(mode)}"


def set_voltage(channel: int, voltage: int | float) -> str:
    output = _channel(channel)
    value = _number(
        voltage,
        name="voltage",
        minimum=VOLTAGE_MIN_V,
        maximum=VOLTAGE_MAX_V,
    )
    return f"VSET:OUT{output} {_format_number(value)}"


def set_offset(channel: int, offset: int | float) -> str:
    output = _channel(channel)
    value = _number(
        offset,
        name="offset",
        minimum=OFFSET_MIN_V,
        maximum=OFFSET_MAX_V,
    )
    return f"VOFS:OUT{output} {_format_number(value)}"


def select_file(file_name: str) -> str:
    return f"SOUR SEGM {_text_argument(file_name, 'file_name')}"


def list_directory(path: str) -> str:
    return f"DIR? {_text_argument(path, 'path')}"


def directory_query(kind: DirectoryKind) -> str:
    if not isinstance(kind, DirectoryKind):
        raise AutoWaveValidationError(f"kind must be DirectoryKind, got {type(kind).__name__}")
    return f"DIR? {kind.value}"


def file_exists_query(path: str) -> str:
    return f"CKFL? {_text_argument(path, 'path')}"


def file_details_query(file_name: str) -> str:
    return f"CKLF? {_text_argument(file_name, 'file_name')}"


def file_duration_query(file_name: str) -> str:
    return f"CKFD? {_text_argument(file_name, 'file_name')}"


def status_test_query() -> str:
    return "STAT? TEST"


def status_output_query(channel: int) -> str:
    return f"STAT? OUT{_channel(channel)}"


def status_input_query(channel: int) -> str:
    return f"STAT? IN{_channel(channel, maximum=2)}"


def status_system_query() -> str:
    return "STAT? SYST"


def status_mac_query() -> str:
    return "STAT? MAC"
