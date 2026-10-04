"""Packaging and compatibility smoke tests for PR01."""

from __future__ import annotations

from importlib import metadata
from importlib.resources import files
from pathlib import Path

import autowave


def test_package_version_matches_repository_version() -> None:
    repo_version = (Path(__file__).resolve().parents[2] / "VERSION").read_text().strip()
    assert autowave.__version__ == repo_version == "0.1.0"


def test_distribution_metadata_matches_package_version() -> None:
    assert metadata.version("autowave-driver") == autowave.__version__


def test_scpi_driver_core_is_exact_expected_version() -> None:
    assert metadata.version("scpi-driver-core") == "0.1.0.dev6"


def test_core_dependency_metadata_pins_reviewed_commit() -> None:
    requirements = metadata.requires("autowave-driver") or []
    core_requirements = [item for item in requirements if item.startswith("scpi-driver-core")]
    assert len(core_requirements) == 1
    assert "d850f88a78ddfbfa08b667c0be6cbb0bb4a01541" in core_requirements[0]


def test_py_typed_marker_is_packaged() -> None:
    assert files("autowave").joinpath("py.typed").is_file()


def test_legacy_top_level_modules_remain_importable() -> None:
    import AutoWave_class
    import Timer_class

    assert hasattr(AutoWave_class, "com_interface")
    assert hasattr(AutoWave_class, "storage")
    assert hasattr(Timer_class, "Timer")
