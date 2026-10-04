"""Public AutoWave driver API tests."""

from __future__ import annotations

from collections import deque

import pytest
from scpi_driver_core.transport import MockTransport, ReplayPolicy, TransportState

from autowave.driver import AutoWave
from autowave.errors import AutoWaveResponseError, AutoWaveValidationError
from autowave.models import DirectoryKind, GeneratorMode, TestStatus, TriggerMode
from autowave.protocol import ACK, encode_command

_IDN = b"*IDN:EM TEST, AutoWave, 0, 5.10.08, 4, 2"


def _bootstrap_steps(idn: bytes = _IDN) -> list[tuple[bytes, bytes | Exception]]:
    return [
        (b"*IDN?", idn),
        (b"*ECHO:ON", b"*ECHO ON:OK"),
        (b"*PRCL:ON", b"*PRCL ON:OK"),
    ]


def _scripted_mock(
    steps: list[tuple[bytes, bytes | Exception]],
) -> tuple[MockTransport, deque[tuple[bytes, bytes | Exception]]]:
    transport = MockTransport(timeout_s=2.0)
    pending = deque(steps)

    def midpoint() -> None:
        assert pending, "unexpected transport transaction"
        expected, outcome = pending.popleft()
        writes = [op.data for op in transport.operations if op.kind == "write"]
        assert writes[-1] == expected
        if isinstance(outcome, Exception):
            transport.fail_next_read(outcome, fault=True)
        else:
            transport.feed(outcome)

    transport.on_transact_midpoint = midpoint
    return transport, pending


def _driver(
    steps: list[tuple[bytes, bytes | Exception]],
    *,
    idn: bytes = _IDN,
) -> tuple[AutoWave, MockTransport, deque[tuple[bytes, bytes | Exception]]]:
    transport, pending = _scripted_mock(_bootstrap_steps(idn) + steps)
    from autowave.connection import AutoWaveConnection

    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    driver = AutoWave(connection, safe_query_retry_policy=None)
    driver.open()
    return driver, transport, pending


def _writes(transport: MockTransport) -> list[bytes]:
    return [op.data for op in transport.operations if op.kind == "write"]


def test_driver_open_close_and_context_state() -> None:
    transport, pending = _scripted_mock(_bootstrap_steps())
    from autowave.connection import AutoWaveConnection

    driver = AutoWave(
        AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0),
        safe_query_retry_policy=None,
    )

    with driver as active:
        assert active is driver
        assert active.is_connected is True
        assert active.protocol_ready is True
        assert active.identity is not None
        assert active.identity.model == "AutoWave"

    assert transport.state is TransportState.CLOSED
    assert driver.is_connected is False
    assert driver.identity is None
    assert not pending


@pytest.mark.parametrize(
    ("method_name", "argument", "command"),
    [
        ("set_generator_mode", GeneratorMode.GENERATOR, "MOD GEN"),
        ("set_generator_mode", GeneratorMode.RECORDER, "MOD REC"),
        ("set_trigger_mode", TriggerMode.MANUAL_START, "TRIG:GEN 1"),
        ("set_trigger_mode", TriggerMode.AUTO, "TRIG:GEN 3"),
    ],
)
def test_mode_setters_send_exact_non_replayable_frame(
    method_name: str,
    argument: object,
    command: str,
) -> None:
    frame = encode_command(command)
    driver, transport, pending = _driver([(frame, bytes((ACK,)))])

    getattr(driver, method_name)(argument)

    assert _writes(transport)[-1] == frame
    assert transport.replay_policies[-1] is ReplayPolicy.NEVER
    assert not pending


def test_voltage_and_negative_offset_send_exact_frames() -> None:
    voltage = encode_command("VSET:OUT1 13.5")
    offset = encode_command("VOFS:OUT2 -5")
    driver, transport, pending = _driver(
        [
            (voltage, bytes((ACK,))),
            (offset, bytes((ACK,))),
        ]
    )

    driver.set_voltage(13.5)
    driver.set_offset(-5, channel=2)

    assert _writes(transport)[-2:] == [voltage, offset]
    assert transport.replay_policies[-2:] == [ReplayPolicy.NEVER, ReplayPolicy.NEVER]
    assert not pending


def test_installed_output_count_is_enforced_before_command_send() -> None:
    driver, transport, pending = _driver([], idn=b"EM TEST,AutoWave,SN1,8.03.02,2,2")
    before = list(_writes(transport))

    with pytest.raises(AutoWaveValidationError, match="installed output count"):
        driver.set_voltage(12.0, channel=3)

    assert _writes(transport) == before
    assert not pending


def test_installed_input_count_is_enforced_before_query_send() -> None:
    driver, transport, pending = _driver([], idn=b"EM TEST,AutoWave,SN1,8.03.02,4,1")
    before = list(_writes(transport))

    with pytest.raises(AutoWaveValidationError, match="installed input count"):
        driver.query_input_status(2)

    assert _writes(transport) == before
    assert not pending


def test_select_file_is_side_effecting_and_never_replayed() -> None:
    frame = encode_command("SOUR SEGM SineTest.dsg")
    driver, transport, pending = _driver([(frame, bytes((ACK,)))])

    driver.select_file("SineTest.dsg")

    assert transport.replay_policies[-1] is ReplayPolicy.NEVER
    assert not pending


def test_query_test_status_returns_typed_status_and_safe_policy() -> None:
    command = encode_command("STAT? TEST")
    response = encode_command("STAT TEST:8,1,2,3,4,5,6")
    driver, transport, pending = _driver([(command, response)])

    status = driver.query_test_status()

    assert status == TestStatus(
        test_state=8,
        output_states=(1, 2, 3, 4),
        input_states=(5, 6),
        raw="STAT TEST:8,1,2,3,4,5,6",
    )
    assert transport.replay_policies[-1] is ReplayPolicy.SAFE
    assert not pending


@pytest.mark.parametrize(
    "response",
    [
        "STAT TEST:1,2",
        "STAT TEST:1,2,3,4,5,6,nope",
        "OTHER:1,2,3,4,5,6,7",
    ],
)
def test_query_test_status_rejects_malformed_payload(response: str) -> None:
    command = encode_command("STAT? TEST")
    driver, _transport, pending = _driver([(command, encode_command(response))])

    with pytest.raises(AutoWaveResponseError):
        driver.query_test_status()

    assert not pending


def test_status_queries_parse_output_and_input_channels() -> None:
    out_cmd = encode_command("STAT? OUT4")
    in_cmd = encode_command("STAT? IN2")
    driver, transport, pending = _driver(
        [
            (out_cmd, encode_command("STAT OUT4:8")),
            (in_cmd, encode_command("STAT IN2:4")),
        ]
    )

    assert driver.query_output_status(4) == 8
    assert driver.query_input_status(2) == 4
    assert transport.replay_policies[-2:] == [ReplayPolicy.SAFE, ReplayPolicy.SAFE]
    assert not pending


@pytest.mark.parametrize(
    ("method", "response"),
    [
        ("query_output_status", "STAT OUT1:not-an-int"),
        ("query_input_status", "WRONG:4"),
    ],
)
def test_scalar_status_queries_reject_bad_response(
    method: str,
    response: str,
) -> None:
    command = "STAT? OUT1" if method == "query_output_status" else "STAT? IN1"
    driver, _transport, pending = _driver(
        [(encode_command(command), encode_command(response))]
    )

    with pytest.raises(AutoWaveResponseError):
        getattr(driver, method)(1)

    assert not pending


def test_system_and_mac_queries() -> None:
    system_cmd = encode_command("STAT? SYST")
    mac_cmd = encode_command("STAT? MAC")
    driver, _transport, pending = _driver(
        [
            (system_cmd, encode_command("STAT SYST:8.03.02")),
            (mac_cmd, encode_command("STAT MAC:00:11:22:33:44:55")),
        ]
    )

    assert driver.query_system_status() == "STAT SYST:8.03.02"
    assert driver.query_mac_address() == "00:11:22:33:44:55"
    assert not pending


def test_directory_queries_keep_upgrade_and_log_distinct() -> None:
    upgd = encode_command("DIR? UPGD")
    logd = encode_command("DIR? LOGD")
    driver, _transport, pending = _driver(
        [
            (upgd, encode_command("DIR UPGD:/upgrade")),
            (logd, encode_command("DIR LOGD:/logs")),
        ]
    )

    assert driver.get_directory(DirectoryKind.UPGRADE) == "/upgrade"
    assert driver.get_directory(DirectoryKind.LOG) == "/logs"
    assert not pending


def test_directory_and_file_metadata_queries_send_exact_commands() -> None:
    list_cmd = encode_command("DIR? /home/guest/DowFiles")
    exists_cmd = encode_command("CKFL? /home/guest/DowFiles/a.dsg")
    details_cmd = encode_command("CKLF? a.dsg")
    duration_cmd = encode_command("CKFD? a.dsg")
    driver, _transport, pending = _driver(
        [
            (list_cmd, encode_command("DIR:/home/guest/DowFiles:a.dsg")),
            (exists_cmd, encode_command("CKFL:1")),
            (details_cmd, encode_command("CKLF:details")),
            (duration_cmd, encode_command("CKFD:120")),
        ]
    )

    assert driver.list_directory("/home/guest/DowFiles") == "DIR:/home/guest/DowFiles:a.dsg"
    assert driver.query_file_exists("/home/guest/DowFiles/a.dsg") == "CKFL:1"
    assert driver.query_file_details("a.dsg") == "CKLF:details"
    assert driver.query_file_duration("a.dsg") == "CKFD:120"
    assert not pending


def test_data_query_rejects_ack_instead_of_inventing_text() -> None:
    command = encode_command("STAT? SYST")
    driver, _transport, pending = _driver([(command, bytes((ACK,)))])

    with pytest.raises(AutoWaveResponseError, match="expected decorated data reply"):
        driver.query_system_status()

    assert not pending


def test_go_to_local_is_unframed_write_and_keeps_transport_open() -> None:
    driver, transport, pending = _driver([])

    driver.go_to_local()

    assert _writes(transport)[-1] == b"*GTL"
    assert driver.is_connected is True
    assert driver.protocol_ready is True
    assert not pending


def test_reset_is_unframed_write_then_closes_connection() -> None:
    driver, transport, pending = _driver([])

    driver.reset()

    assert _writes(transport)[-1] == b"*RST"
    assert transport.state is TransportState.CLOSED
    assert driver.is_connected is False
    assert driver.identity is None
    assert not pending


def test_echo_control_does_not_change_protocol_ready_state() -> None:
    driver, transport, pending = _driver(
        [
            (b"*ECHO:OFF", b"*ECHO OFF:OK"),
            (b"*ECHO:ON", b"*ECHO ON:OK"),
        ]
    )

    assert driver.set_echo_enabled(False) == "*ECHO OFF:OK"
    assert driver.protocol_ready is True
    assert driver.set_echo_enabled(True) == "*ECHO ON:OK"
    assert driver.protocol_ready is True
    assert _writes(transport)[-2:] == [b"*ECHO:OFF", b"*ECHO:ON"]
    assert not pending


def test_protocol_control_updates_cached_readiness() -> None:
    driver, transport, pending = _driver(
        [
            (b"*PRCL:OFF", b"*PRCL OFF:OK"),
            (b"*PRCL:ON", b"*PRCL ON:OK"),
        ]
    )

    assert driver.set_protocol_enabled(False) == "*PRCL OFF:OK"
    assert driver.protocol_ready is False
    assert driver.set_protocol_enabled(True) == "*PRCL ON:OK"
    assert driver.protocol_ready is True
    assert _writes(transport)[-2:] == [b"*PRCL:OFF", b"*PRCL:ON"]
    assert not pending


@pytest.mark.parametrize("method_name", ["set_echo_enabled", "set_protocol_enabled"])
def test_control_state_setters_require_bool(method_name: str) -> None:
    driver, transport, pending = _driver([])
    before = list(_writes(transport))

    with pytest.raises(AutoWaveValidationError):
        getattr(driver, method_name)(1)

    assert _writes(transport) == before
    assert not pending
