"""Unit tests for AutoWave connection/session integration."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import pytest
from scpi_driver_core.exceptions import TransportTimeoutError
from scpi_driver_core.execution import RetryPolicy
from scpi_driver_core.transport import MockTransport, ReplayPolicy, TransportState

from autowave.connection import (
    AutoWaveConnection,
    parse_autowave_identity,
    require_single_autowave,
)
from autowave.errors import (
    AutoWaveBusyError,
    AutoWaveConnectionStateError,
    AutoWaveDiscoveryError,
    AutoWaveIdentityError,
    AutoWaveNakError,
    AutoWaveNotReadyError,
    AutoWaveValidationError,
)
from autowave.models import AutoWaveIdentity, BusyPolicy, DiscoveredAutoWave
from autowave.protocol import ACK, BUSY, NAK, NOT_READY, AutoWaveReplyKind, encode_command

_IDN = b"*IDN:EM TEST, AutoWave, 0, 5.10.08, 4, 2"


@dataclass
class FakeClock:
    value: float = 0.0

    def __post_init__(self) -> None:
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.value

    def sleep(self, delay: float) -> None:
        assert delay >= 0
        self.sleeps.append(delay)
        self.value += delay


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


def _write_messages(transport: MockTransport) -> list[bytes]:
    return [op.data for op in transport.operations if op.kind == "write"]


def test_parse_full_vendor_identity() -> None:
    identity = parse_autowave_identity(_IDN.decode("ascii"))

    assert identity == AutoWaveIdentity(
        manufacturer="EM TEST",
        model="AutoWave",
        serial_number="0",
        firmware_version="5.10.08",
        outputs=4,
        inputs=2,
        raw=_IDN.decode("ascii"),
    )


def test_parse_identity_without_vendor_prefix_and_optional_tail() -> None:
    identity = parse_autowave_identity("EM TEST,AutoWave,SN42,8.03.02")
    assert identity.manufacturer == "EM TEST"
    assert identity.model == "AutoWave"
    assert identity.serial_number == "SN42"
    assert identity.firmware_version == "8.03.02"
    assert identity.outputs is None
    assert identity.inputs is None


@pytest.mark.parametrize(
    "response",
    [
        "",
        "EM TEST",
        "OTHER,AutoWave,0,1.0",
        "EM TEST,Other,0,1.0",
        "EM TEST,AutoWave,0,1.0,nope,2",
        "EM TEST,AutoWave,0,1.0,4,-1",
    ],
)
def test_invalid_identity_is_rejected(response: str) -> None:
    with pytest.raises(AutoWaveIdentityError):
        parse_autowave_identity(response)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"attempts": 0}, "attempts"),
        ({"attempts": True}, "attempts"),
        ({"max_elapsed_s": 0.0}, "max_elapsed_s"),
        ({"max_elapsed_s": float("inf")}, "max_elapsed_s"),
    ],
)
def test_busy_policy_rejects_invalid_bounds(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(AutoWaveValidationError, match=message):
        BusyPolicy(**kwargs)  # type: ignore[arg-type]


def test_open_bootstraps_exact_unframed_sequence_and_identity() -> None:
    transport, pending = _scripted_mock(_bootstrap_steps())
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)

    identity = connection.open()

    assert identity.model == "AutoWave"
    assert identity.outputs == 4
    assert connection.identity == identity
    assert connection.is_connected is True
    assert connection.protocol_ready is True
    assert _write_messages(transport) == [b"*IDN?", b"*ECHO:ON", b"*PRCL:ON"]
    assert all(op.timeout_s == 2.0 for op in transport.operations if op.kind in {"write", "read"})
    assert not pending


def test_second_open_is_idempotent_after_successful_bootstrap() -> None:
    transport, pending = _scripted_mock(_bootstrap_steps())
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)

    first = connection.open()
    writes_after_first = list(_write_messages(transport))
    second = connection.open()

    assert second is first
    assert _write_messages(transport) == writes_after_first
    assert not pending


def test_invalid_identity_closes_transport_and_clears_protocol_state() -> None:
    transport, pending = _scripted_mock([(b"*IDN?", b"OTHER,Instrument,0,1.0")])
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)

    with pytest.raises(AutoWaveIdentityError):
        connection.open()

    assert transport.state is TransportState.CLOSED
    assert connection.identity is None
    assert connection.protocol_ready is False
    assert not pending


def test_close_is_idempotent_and_sends_no_device_command() -> None:
    transport, pending = _scripted_mock(_bootstrap_steps())
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()
    before_close = list(_write_messages(transport))

    connection.close()
    connection.close()

    assert _write_messages(transport) == before_close
    assert transport.release_count == 1
    assert connection.identity is None
    assert connection.protocol_ready is False
    assert not pending


def test_context_manager_bootstraps_and_closes() -> None:
    transport, pending = _scripted_mock(_bootstrap_steps())
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)

    with connection as active:
        assert active.protocol_ready is True

    assert transport.state is TransportState.CLOSED
    assert not pending


def test_pacing_is_between_transactions_not_between_write_and_read() -> None:
    clock = FakeClock()
    frame = encode_command("STAT? TEST")
    transport, pending = _scripted_mock(_bootstrap_steps() + [(frame, bytes((ACK,)))])
    connection = AutoWaveConnection.from_transport(
        transport,
        minimum_interval_s=0.25,
        sleep=clock.sleep,
        now=clock.now,
    )

    connection.open()
    assert clock.sleeps == [0.25, 0.25]

    connection.transact_framed("STAT? TEST")
    assert clock.sleeps == [0.25, 0.25, 0.25]
    assert not pending


def test_framed_ack_uses_exact_frame_and_never_replay_by_default() -> None:
    frame = encode_command("MOD GEN")
    transport, pending = _scripted_mock(_bootstrap_steps() + [(frame, bytes((ACK,)))])
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()

    reply = connection.transact_framed("MOD GEN")

    assert reply.kind is AutoWaveReplyKind.ACK
    assert _write_messages(transport)[-1] == frame
    assert transport.replay_policies[-1] is ReplayPolicy.NEVER
    assert not pending


def test_framed_data_reply_is_returned_as_parsed_payload() -> None:
    frame = encode_command("STAT? TEST")
    response = encode_command("STAT TEST:8,8,8,8,4,4,0")
    transport, pending = _scripted_mock(_bootstrap_steps() + [(frame, response)])
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()

    reply = connection.transact_framed("STAT? TEST", replay_policy=ReplayPolicy.SAFE)

    assert reply.kind is AutoWaveReplyKind.DATA
    assert reply.payload == b"STAT TEST:8,8,8,8,4,4,0"
    assert transport.replay_policies[-1] is ReplayPolicy.SAFE
    assert not pending


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (NAK, AutoWaveNakError),
        (NOT_READY, AutoWaveNotReadyError),
    ],
)
def test_nak_and_notready_are_not_replayed(
    status: int,
    error_type: type[Exception],
) -> None:
    frame = encode_command("MOD GEN")
    transport, pending = _scripted_mock(_bootstrap_steps() + [(frame, bytes((status,)))])
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()

    with pytest.raises(error_type):
        connection.transact_framed("MOD GEN")

    assert _write_messages(transport).count(frame) == 1
    assert not pending


def test_busy_resends_only_the_exact_same_frame_until_ack() -> None:
    frame = encode_command("MOD GEN")
    transport, pending = _scripted_mock(
        _bootstrap_steps()
        + [
            (frame, bytes((BUSY,))),
            (frame, bytes((BUSY,))),
            (frame, bytes((ACK,))),
        ]
    )
    connection = AutoWaveConnection.from_transport(
        transport,
        minimum_interval_s=0.0,
        busy_policy=BusyPolicy(attempts=5, max_elapsed_s=5.0),
    )
    connection.open()

    reply = connection.transact_framed("MOD GEN")

    assert reply.kind is AutoWaveReplyKind.ACK
    assert _write_messages(transport).count(frame) == 3
    assert not pending


def test_busy_attempt_bound_raises_typed_error() -> None:
    frame = encode_command("MOD GEN")
    transport, pending = _scripted_mock(
        _bootstrap_steps()
        + [
            (frame, bytes((BUSY,))),
            (frame, bytes((BUSY,))),
            (frame, bytes((BUSY,))),
        ]
    )
    connection = AutoWaveConnection.from_transport(
        transport,
        minimum_interval_s=0.0,
        busy_policy=BusyPolicy(attempts=3, max_elapsed_s=5.0),
    )
    connection.open()

    with pytest.raises(AutoWaveBusyError) as caught:
        connection.transact_framed("MOD GEN")

    assert caught.value.attempts == 3
    assert caught.value.raw == bytes((BUSY,))
    assert _write_messages(transport).count(frame) == 3
    assert not pending


def test_busy_elapsed_bound_prevents_another_send() -> None:
    clock = FakeClock()
    frame = encode_command("MOD GEN")
    transport, pending = _scripted_mock(
        _bootstrap_steps()
        + [
            (frame, bytes((BUSY,))),
            (frame, bytes((BUSY,))),
        ]
    )
    connection = AutoWaveConnection.from_transport(
        transport,
        minimum_interval_s=0.25,
        busy_policy=BusyPolicy(attempts=10, max_elapsed_s=0.40),
        sleep=clock.sleep,
        now=clock.now,
    )
    connection.open()

    with pytest.raises(AutoWaveBusyError) as caught:
        connection.transact_framed("MOD GEN")

    assert caught.value.attempts == 2
    assert _write_messages(transport).count(frame) == 2
    assert not pending


def test_transport_timeout_is_not_replayed_by_default_and_invalidates_cached_state() -> None:
    frame = encode_command("MOD GEN")
    transport, pending = _scripted_mock(
        _bootstrap_steps() + [(frame, TransportTimeoutError("read timed out"))]
    )
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()

    with pytest.raises(TransportTimeoutError):
        connection.transact_framed("MOD GEN")

    assert transport.state is TransportState.FAULTED
    assert connection.protocol_ready is False
    assert connection.identity is None
    assert _write_messages(transport).count(frame) == 1
    assert not pending


def test_safe_retry_recovers_bootstrap_then_replays_query_once() -> None:
    frame = encode_command("STAT? TEST")
    data_reply = encode_command("STAT TEST:8,8,8,8,4,4,0")
    transport, pending = _scripted_mock(
        _bootstrap_steps()
        + [(frame, TransportTimeoutError("read timed out"))]
        + _bootstrap_steps()
        + [(frame, data_reply)]
    )
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()

    reply = connection.transact_framed(
        "STAT? TEST",
        replay_policy=ReplayPolicy.SAFE,
        retry_policy=RetryPolicy.constant(attempts=2, delay_s=0.0),
    )

    assert reply.payload == b"STAT TEST:8,8,8,8,4,4,0"
    assert transport.open_count == 2
    assert _write_messages(transport) == [
        b"*IDN?",
        b"*ECHO:ON",
        b"*PRCL:ON",
        frame,
        b"*IDN?",
        b"*ECHO:ON",
        b"*PRCL:ON",
        frame,
    ]
    assert not pending


def test_retry_policy_is_rejected_for_non_replayable_framed_operation() -> None:
    transport, pending = _scripted_mock(_bootstrap_steps())
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()
    before = list(_write_messages(transport))

    with pytest.raises(AutoWaveValidationError, match="ReplayPolicy.SAFE"):
        connection.transact_framed(
            "STAR",
            retry_policy=RetryPolicy(attempts=2),
        )

    assert _write_messages(transport) == before
    assert not pending


def test_recover_requires_faulted_transport() -> None:
    transport, pending = _scripted_mock(_bootstrap_steps())
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()

    with pytest.raises(AutoWaveConnectionStateError, match="FAULTED"):
        connection.recover()

    assert not pending


def test_failed_recovery_bootstrap_closes_reopened_transport() -> None:
    frame = encode_command("STAT? TEST")
    transport, pending = _scripted_mock(
        _bootstrap_steps()
        + [(frame, TransportTimeoutError("read timed out"))]
        + [(b"*IDN?", b"OTHER,Instrument,0,1.0")]
    )
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()

    with pytest.raises(AutoWaveIdentityError):
        connection.transact_framed(
            "STAT? TEST",
            replay_policy=ReplayPolicy.SAFE,
            retry_policy=RetryPolicy.constant(attempts=2, delay_s=0.0),
        )

    assert transport.state is TransportState.CLOSED
    assert connection.protocol_ready is False
    assert connection.identity is None
    assert not pending


def test_control_transaction_requires_star_command_and_connection() -> None:
    transport = MockTransport()
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)

    with pytest.raises(AutoWaveConnectionStateError):
        connection.control_transaction("*IDN?")

    transport2, pending = _scripted_mock(_bootstrap_steps())
    connection2 = AutoWaveConnection.from_transport(transport2, minimum_interval_s=0.0)
    connection2.open()
    with pytest.raises(AutoWaveValidationError, match="begin with"):
        connection2.control_transaction("REB")
    assert not pending


def test_control_retry_requires_safe_replay_classification() -> None:
    transport, pending = _scripted_mock(_bootstrap_steps())
    connection = AutoWaveConnection.from_transport(transport, minimum_interval_s=0.0)
    connection.open()

    with pytest.raises(AutoWaveValidationError, match="ReplayPolicy.SAFE"):
        connection.control_transaction("*IDN?", retry_policy=RetryPolicy(attempts=2))

    assert not pending


def test_framed_transaction_requires_successful_bootstrap() -> None:
    connection = AutoWaveConnection.from_transport(MockTransport(), minimum_interval_s=0.0)

    with pytest.raises(AutoWaveConnectionStateError, match="call open"):
        connection.transact_framed("STAT? TEST")


@pytest.mark.parametrize(
    "resource",
    ["", "TCPIP0::192.0.2.1::INSTR", "ASRL1::INSTR", "GPIB0::5"],
)
def test_visa_factory_rejects_non_target_resource_shapes(resource: str) -> None:
    with pytest.raises(AutoWaveValidationError):
        AutoWaveConnection.visa(resource)


def test_visa_factory_accepts_explicit_gpib_instr_without_opening() -> None:
    connection = AutoWaveConnection.visa("GPIB0::5::INSTR")
    assert connection.session.transport.descriptor.address == "GPIB0::5::INSTR"
    assert connection.is_connected is False


def test_require_single_discovery_result_never_silently_chooses() -> None:
    identity = parse_autowave_identity(_IDN.decode("ascii"))
    one = DiscoveredAutoWave("GPIB0::5::INSTR", identity)
    two = DiscoveredAutoWave("GPIB0::6::INSTR", identity)

    assert require_single_autowave([one]) is one
    with pytest.raises(AutoWaveDiscoveryError, match="no AutoWave"):
        require_single_autowave([])
    with pytest.raises(AutoWaveDiscoveryError, match="multiple"):
        require_single_autowave([one, two])
