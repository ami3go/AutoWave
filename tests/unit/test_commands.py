"""Unit tests for validated AutoWave command construction."""

from __future__ import annotations

import pytest

from autowave import commands
from autowave.errors import AutoWaveValidationError
from autowave.models import DirectoryKind, GeneratorMode, TriggerMode


def test_generator_mode_commands() -> None:
    assert commands.set_generator_mode(GeneratorMode.GENERATOR) == "MOD GEN"
    assert commands.set_generator_mode(GeneratorMode.RECORDER) == "MOD REC"
    assert commands.set_generator_mode(GeneratorMode.GENERATOR_RECORDER) == "MOD GNRC"


def test_trigger_mode_commands_cover_documented_values() -> None:
    assert commands.set_trigger_mode(TriggerMode.OFF) == "TRIG:GEN 0"
    assert commands.set_trigger_mode(TriggerMode.MANUAL_START) == "TRIG:GEN 1"
    assert commands.set_trigger_mode(TriggerMode.TRIGGER_INPUT_START) == "TRIG:GEN 2"
    assert commands.set_trigger_mode(TriggerMode.AUTO) == "TRIG:GEN 3"
    assert commands.set_trigger_mode(TriggerMode.MANUAL_EVENT) == "TRIG:GEN 4"
    assert commands.set_trigger_mode(TriggerMode.TRIGGER_INPUT_EVENT) == "TRIG:GEN 5"
    assert commands.set_trigger_mode(TriggerMode.MANUAL_ITERATION) == "TRIG:GEN 6"
    assert commands.set_trigger_mode(TriggerMode.TRIGGER_INPUT_ITERATION) == "TRIG:GEN 7"


def test_voltage_command_boundaries_and_formatting() -> None:
    assert commands.set_voltage(1, 0) == "VSET:OUT1 0"
    assert commands.set_voltage(4, 13.5) == "VSET:OUT4 13.5"
    assert commands.set_voltage(2, 60.0) == "VSET:OUT2 60"


def test_offset_preserves_valid_negative_values() -> None:
    assert commands.set_offset(1, -5) == "VOFS:OUT1 -5"
    assert commands.set_offset(4, -60.0) == "VOFS:OUT4 -60"
    assert commands.set_offset(2, 60.0) == "VOFS:OUT2 60"
    assert commands.set_offset(3, -0.0) == "VOFS:OUT3 0"


@pytest.mark.parametrize("channel", [0, 5, -1, True, 1.5])
def test_invalid_output_channels_are_rejected(channel: object) -> None:
    with pytest.raises(AutoWaveValidationError):
        commands.set_voltage(channel, 1.0)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [-0.1, 60.1, float("inf"), float("nan"), True, "13.5"])
def test_invalid_voltage_is_rejected(value: object) -> None:
    with pytest.raises(AutoWaveValidationError):
        commands.set_voltage(1, value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [-60.1, 60.1, float("inf"), float("nan"), True, "-5"])
def test_invalid_offset_is_rejected(value: object) -> None:
    with pytest.raises(AutoWaveValidationError):
        commands.set_offset(1, value)  # type: ignore[arg-type]


def test_file_and_directory_commands() -> None:
    assert commands.select_file("SineTest.dsg") == "SOUR SEGM SineTest.dsg"
    assert commands.list_directory("/home/guest/DowFiles") == "DIR? /home/guest/DowFiles"
    assert commands.directory_query(DirectoryKind.DOWNLOAD) == "DIR? DOWD"
    assert commands.directory_query(DirectoryKind.RECORD) == "DIR? RECD"
    assert commands.directory_query(DirectoryKind.UPGRADE) == "DIR? UPGD"
    assert commands.directory_query(DirectoryKind.LOG) == "DIR? LOGD"
    assert commands.file_exists_query("/tmp/a.dsg") == "CKFL? /tmp/a.dsg"
    assert commands.file_details_query("a.dsg") == "CKLF? a.dsg"
    assert commands.file_duration_query("a.dsg") == "CKFD? a.dsg"


@pytest.mark.parametrize("value", ["", "a\nb", "a\rb"])
def test_text_arguments_reject_empty_or_line_breaks(value: str) -> None:
    with pytest.raises(AutoWaveValidationError):
        commands.select_file(value)


def test_non_string_text_argument_is_rejected() -> None:
    with pytest.raises(AutoWaveValidationError):
        commands.list_directory(123)  # type: ignore[arg-type]


def test_status_commands() -> None:
    assert commands.status_test_query() == "STAT? TEST"
    assert commands.status_output_query(1) == "STAT? OUT1"
    assert commands.status_output_query(4) == "STAT? OUT4"
    assert commands.status_input_query(1) == "STAT? IN1"
    assert commands.status_input_query(2) == "STAT? IN2"
    assert commands.status_system_query() == "STAT? SYST"
    assert commands.status_mac_query() == "STAT? MAC"


def test_invalid_enum_types_are_rejected() -> None:
    with pytest.raises(AutoWaveValidationError):
        commands.set_generator_mode("GEN")  # type: ignore[arg-type]
    with pytest.raises(AutoWaveValidationError):
        commands.set_trigger_mode(1)  # type: ignore[arg-type]
    with pytest.raises(AutoWaveValidationError):
        commands.directory_query("DOWD")  # type: ignore[arg-type]


@pytest.mark.parametrize("channel", [0, 3, -1, True])
def test_invalid_input_status_channel_is_rejected(channel: object) -> None:
    with pytest.raises(AutoWaveValidationError):
        commands.status_input_query(channel)  # type: ignore[arg-type]
