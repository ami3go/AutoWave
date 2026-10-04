"""PyVISA-sim integration for the real AutoWave VISA construction path."""

from __future__ import annotations

from pathlib import Path

import pytest
import pyvisa

from autowave.connection import AutoWaveConnection, discover_autowave_resources

_SIM_DEFINITION = Path(__file__).with_name("fixtures") / "autowave_pyvisa_sim.yaml"

pytestmark = [pytest.mark.integration, pytest.mark.visa_sim]


def test_visa_connection_bootstraps_without_text_terminators() -> None:
    connection = AutoWaveConnection.visa(
        "GPIB0::5::INSTR",
        visa_library=f"{_SIM_DEFINITION.resolve()}@sim",
        minimum_interval_s=0.0,
    )

    with connection as active:
        assert active.identity is not None
        assert active.identity.manufacturer == "EM TEST"
        assert active.identity.model == "AutoWave"
        assert active.identity.firmware_version == "8.03.02"
        assert active.identity.outputs == 4
        assert active.identity.inputs == 2
        assert active.protocol_ready is True

    assert connection.is_connected is False


def test_visa_discovery_uses_borrowed_manager_and_bounded_idn_query() -> None:
    manager = pyvisa.ResourceManager(f"{_SIM_DEFINITION.resolve()}@sim")
    found = discover_autowave_resources(manager, timeout_s=0.5)

    assert len(found) == 1
    assert found[0].resource_name == "GPIB0::5::INSTR"
    assert found[0].identity.model == "AutoWave"
