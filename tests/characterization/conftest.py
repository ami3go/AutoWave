"""Fixtures for characterizing the pre-migration AutoWave driver.

These tests intentionally load the legacy module without requiring a real VISA
installation or instrument.  PR00 must describe the existing behavior before
runtime code is refactored.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEGACY_SOURCE = _REPO_ROOT / "src" / "AutoWave_class.py"


@pytest.fixture
def legacy_module(monkeypatch: pytest.MonkeyPatch):
    """Load the legacy driver with a minimal PyVISA import stub."""

    fake_pyvisa = types.ModuleType("pyvisa")
    fake_pyvisa.constants = types.SimpleNamespace(VI_ATTR_SEND_END_EN=1)
    fake_pyvisa.ResourceManager = lambda: None
    monkeypatch.setitem(sys.modules, "pyvisa", fake_pyvisa)

    module_name = "autowave_legacy_characterization"
    spec = importlib.util.spec_from_file_location(module_name, _LEGACY_SOURCE)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
