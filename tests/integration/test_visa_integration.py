"""PyVISA-sim integration for the AutoWave unframed bootstrap path."""

from __future__ import annotations

from pathlib import Path

import pytest

from autowave.connection import AutoWaveConnection

_SIM_DEFINITION = Path(__file__).with_name("fixtures") / "autowave_pyvisa_sim.yaml"

pytestmark = [pytest.mark.integration, pytest.mark.visa_sim]


def test_visa_transport_bootstrap_through_pyvisa_sim() -> None:
    connection = AutoWaveConnection.visa(
        "GPIB0::5::INSTR",
        timeout_s=1.0,
        minimum_interval_s=0.0,
        visa_library=f"{_SIM_DEFINITION.resolve()}@sim",
    )

    identity = connection.open()
    try:
        assert identity.manufacturer == "EM TEST"
        assert identity.model == "AutoWave"
        assert identity.serial_number == "0"
        assert identity.firmware_version == "8.03.02"
        assert identity.outputs == 4
        assert identity.inputs == 2
        assert connection.protocol_ready is True
    finally:
        connection.close()

    assert connection.is_connected is False
    assert connection.protocol_ready is False
