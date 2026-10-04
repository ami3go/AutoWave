"""AutoWave connection/session integration on top of scpi-driver-core.

This layer owns communication bootstrap, bounded framed transactions, vendor
BUSY re-query semantics, safe-query recovery, and explicit VISA construction.
High-level device workflows remain outside this module.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable
from contextlib import suppress
from types import TracebackType
from typing import Any, Final

from scpi_driver_core import ScpiClient, ScpiDriverError, ScpiSession, TransportError
from scpi_driver_core.execution import RetryPolicy, run_with_retry
from scpi_driver_core.scpi import ScpiTextCodec, parse_csv
from scpi_driver_core.transport import (
    ReadMode,
    ReadRequest,
    ReplayPolicy,
    Transport,
    TransportState,
    VisaTransport,
)

from autowave.errors import (
    AutoWaveBusyError,
    AutoWaveConnectionStateError,
    AutoWaveDiscoveryError,
    AutoWaveIdentityError,
    AutoWaveValidationError,
)
from autowave.models import DEFAULT_BUSY_POLICY, AutoWaveIdentity, BusyPolicy, DiscoveredAutoWave
from autowave.protocol import (
    DEFAULT_MAX_COMMAND_PAYLOAD,
    DEFAULT_MAX_RESPONSE_SIZE,
    AutoWaveReply,
    AutoWaveReplyKind,
    encode_command,
    parse_reply,
    raise_for_status,
)

__all__ = [
    "DEFAULT_COMMUNICATION_TIMEOUT_S",
    "DEFAULT_DISCOVERY_TIMEOUT_S",
    "DEFAULT_MINIMUM_INTERVAL_S",
    "AutoWaveConnection",
    "discover_autowave_resources",
    "parse_autowave_identity",
    "require_single_autowave",
]

DEFAULT_COMMUNICATION_TIMEOUT_S: Final = 2.0
DEFAULT_DISCOVERY_TIMEOUT_S: Final = 0.5
DEFAULT_MINIMUM_INTERVAL_S: Final = 0.250

Sleep = Callable[[float], None]
Clock = Callable[[], float]


def _validate_positive_finite(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AutoWaveValidationError(f"{name} must be a finite positive number, got {value!r}")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise AutoWaveValidationError(f"{name} must be a finite positive number, got {value!r}")


def _validate_nonnegative_finite(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AutoWaveValidationError(f"{name} must be a finite non-negative number, got {value!r}")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise AutoWaveValidationError(
            f"{name} must be a finite non-negative number, got {value!r}"
        )


def _optional_field(fields: list[str], index: int) -> str | None:
    if index >= len(fields):
        return None
    value = fields[index].strip()
    return value or None


def _optional_int(fields: list[str], index: int, name: str, raw: str) -> int | None:
    value = _optional_field(fields, index)
    if value is None:
        return None
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise AutoWaveIdentityError(
            f"AutoWave *IDN? {name} field is not an integer: {value!r}; raw={raw!r}"
        ) from exc
    if parsed < 0:
        raise AutoWaveIdentityError(
            f"AutoWave *IDN? {name} field must be non-negative: {value!r}; raw={raw!r}"
        )
    return parsed


def parse_autowave_identity(response: str) -> AutoWaveIdentity:
    """Parse and validate the vendor-specific AutoWave *IDN? response."""

    try:
        fields = [field.strip() for field in parse_csv(response)]
    except ScpiDriverError as exc:
        raise AutoWaveIdentityError(f"malformed AutoWave *IDN? response {response!r}") from exc

    if len(fields) < 2:
        raise AutoWaveIdentityError(f"AutoWave *IDN? response has too few fields: {response!r}")

    manufacturer = fields[0]
    prefix = "*IDN:"
    if manufacturer.upper().startswith(prefix):
        manufacturer = manufacturer[len(prefix) :].strip()

    model = fields[1].strip()
    if manufacturer.casefold() != "em test":
        raise AutoWaveIdentityError(
            f"expected AutoWave manufacturer 'EM TEST', got {manufacturer!r}; raw={response!r}"
        )
    if model.casefold() != "autowave":
        raise AutoWaveIdentityError(
            f"expected AutoWave model 'AutoWave', got {model!r}; raw={response!r}"
        )

    return AutoWaveIdentity(
        manufacturer=manufacturer,
        model=model,
        serial_number=_optional_field(fields, 2),
        firmware_version=_optional_field(fields, 3),
        outputs=_optional_int(fields, 4, "outputs", response),
        inputs=_optional_int(fields, 5, "inputs", response),
        raw=response,
    )


def _control_codec() -> ScpiTextCodec:
    return ScpiTextCodec(
        encoding="ascii",
        command_terminator=b"",
        response_terminator=None,
        maximum_command_size=DEFAULT_MAX_COMMAND_PAYLOAD,
        maximum_response_size=DEFAULT_MAX_RESPONSE_SIZE,
    )


def _response_request() -> ReadRequest:
    return ReadRequest(
        mode=ReadMode.BACKEND_DEFINED_MESSAGE,
        maximum_size=DEFAULT_MAX_RESPONSE_SIZE,
    )


def _build_client(
    transport: Transport,
    *,
    timeout_s: float,
    minimum_interval_s: float,
    sleep: Sleep,
    now: Clock,
) -> ScpiClient:
    _validate_positive_finite(timeout_s, "timeout_s")
    _validate_nonnegative_finite(minimum_interval_s, "minimum_interval_s")
    return ScpiClient(
        transport,
        codec=_control_codec(),
        response_request=_response_request(),
        timeout_s=float(timeout_s),
        minimum_interval_s=float(minimum_interval_s) if minimum_interval_s > 0 else None,
        sleep=sleep,
        now=now,
    )


class AutoWaveConnection:
    """One bootstrapped AutoWave communication session."""

    def __init__(
        self,
        session: ScpiSession,
        *,
        minimum_interval_s: float = DEFAULT_MINIMUM_INTERVAL_S,
        busy_policy: BusyPolicy = DEFAULT_BUSY_POLICY,
        sleep: Sleep = time.sleep,
        now: Clock = time.monotonic,
    ) -> None:
        _validate_nonnegative_finite(minimum_interval_s, "minimum_interval_s")
        self._session = session
        self._minimum_interval_s = float(minimum_interval_s)
        self._busy_policy = busy_policy
        self._sleep = sleep
        self._now = now
        self._identity: AutoWaveIdentity | None = None
        self._protocol_ready = False

    @classmethod
    def from_transport(
        cls,
        transport: Transport,
        *,
        alias: str = "autowave",
        timeout_s: float = DEFAULT_COMMUNICATION_TIMEOUT_S,
        minimum_interval_s: float = DEFAULT_MINIMUM_INTERVAL_S,
        busy_policy: BusyPolicy = DEFAULT_BUSY_POLICY,
        sleep: Sleep = time.sleep,
        now: Clock = time.monotonic,
    ) -> AutoWaveConnection:
        """Build an AutoWave session around any core byte transport."""

        client = _build_client(
            transport,
            timeout_s=timeout_s,
            minimum_interval_s=minimum_interval_s,
            sleep=sleep,
            now=now,
        )
        session = ScpiSession(alias, client, communication_timeout_s=float(timeout_s))
        return cls(
            session,
            minimum_interval_s=minimum_interval_s,
            busy_policy=busy_policy,
            sleep=sleep,
            now=now,
        )

    @classmethod
    def visa(
        cls,
        resource_name: str,
        *,
        alias: str = "autowave",
        timeout_s: float = DEFAULT_COMMUNICATION_TIMEOUT_S,
        minimum_interval_s: float = DEFAULT_MINIMUM_INTERVAL_S,
        busy_policy: BusyPolicy = DEFAULT_BUSY_POLICY,
        resource_manager: Any | None = None,
        visa_library: str = "",
        sleep: Sleep = time.sleep,
        now: Clock = time.monotonic,
    ) -> AutoWaveConnection:
        """Build the initial production GPIB/VISA AutoWave connection."""

        _validate_gpib_resource(resource_name)
        _validate_positive_finite(timeout_s, "timeout_s")
        _validate_nonnegative_finite(minimum_interval_s, "minimum_interval_s")
        transport = VisaTransport(
            resource_name,
            timeout_s=float(timeout_s),
            resource_manager=resource_manager,
            visa_library=visa_library,
        )
        return cls.from_transport(
            transport,
            alias=alias,
            timeout_s=timeout_s,
            minimum_interval_s=minimum_interval_s,
            busy_policy=busy_policy,
            sleep=sleep,
            now=now,
        )

    @property
    def session(self) -> ScpiSession:
        return self._session

    @property
    def client(self) -> ScpiClient:
        return self._session.client

    @property
    def identity(self) -> AutoWaveIdentity | None:
        return self._identity

    @property
    def is_connected(self) -> bool:
        return self._session.is_connected

    @property
    def protocol_ready(self) -> bool:
        return self._protocol_ready and self._session.is_connected

    def open(self) -> AutoWaveIdentity:
        """Open the transport and complete the verified AutoWave bootstrap."""

        if self.protocol_ready and self._identity is not None:
            return self._identity

        if not self._session.is_connected:
            self._session.open()
        try:
            return self._bootstrap()
        except BaseException:
            self._protocol_ready = False
            self._identity = None
            with suppress(Exception):
                self._session.close()
            raise

    def close(self) -> None:
        """Close transport ownership without sending physical-state commands."""

        self._protocol_ready = False
        self._identity = None
        self._session.close()

    def recover(self) -> AutoWaveIdentity:
        """Recover a faulted transport and re-run communication bootstrap only."""

        if self._session.transport.state is not TransportState.FAULTED:
            raise AutoWaveConnectionStateError(
                "AutoWave recovery is allowed only for a FAULTED transport"
            )
        self._protocol_ready = False
        self._identity = None
        self._session.recover_if_faulted()
        try:
            return self._bootstrap()
        except BaseException:
            self._protocol_ready = False
            self._identity = None
            with suppress(Exception):
                self._session.close()
            raise

    def control_write(self, command: str, *, timeout_s: float | None = None) -> None:
        """Send one unframed star command without assuming a response."""

        self._require_connected()
        self._validate_control_command(command)
        try:
            self.client.write(command, timeout_s=timeout_s)
        except TransportError:
            self._clear_protocol_state()
            raise

    def control_transaction(
        self,
        command: str,
        *,
        replay_policy: ReplayPolicy = ReplayPolicy.NEVER,
        retry_policy: RetryPolicy | None = None,
        timeout_s: float | None = None,
    ) -> str:
        """Execute one unframed star command and consume its text response."""

        self._require_connected()
        self._validate_control_command(command)
        if (
            retry_policy is not None
            and retry_policy.retries
            and replay_policy is not ReplayPolicy.SAFE
        ):
            raise AutoWaveValidationError(
                "retrying a control transaction requires replay_policy=ReplayPolicy.SAFE"
            )
        try:
            return self.client.query(
                command,
                timeout_s=timeout_s,
                replay_policy=replay_policy,
                retry_policy=retry_policy,
                before_retry=self.recover if retry_policy is not None else None,
            )
        except TransportError:
            self._clear_protocol_state()
            raise

    def transact_framed(
        self,
        command: str,
        *,
        replay_policy: ReplayPolicy = ReplayPolicy.NEVER,
        retry_policy: RetryPolicy | None = None,
        busy_policy: BusyPolicy | None = None,
        timeout_s: float | None = None,
    ) -> AutoWaveReply:
        """Execute one framed command with bounded BUSY and optional safe retry."""

        self._require_protocol_ready()
        if (
            retry_policy is not None
            and retry_policy.retries
            and replay_policy is not ReplayPolicy.SAFE
        ):
            raise AutoWaveValidationError(
                "retrying a framed transaction requires replay_policy=ReplayPolicy.SAFE"
            )

        frame = encode_command(command)
        selected_busy = self._busy_policy if busy_policy is None else busy_policy

        def operation() -> AutoWaveReply:
            return self._transact_frame_with_busy(
                frame,
                replay_policy=replay_policy,
                busy_policy=selected_busy,
                timeout_s=timeout_s,
            )

        if retry_policy is None:
            return operation()

        return run_with_retry(
            operation,
            policy=retry_policy,
            retry_on=(TransportError,),
            sleep=self._sleep,
            now=self._now,
            before_retry=self.recover,
        )

    def __enter__(self) -> AutoWaveConnection:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _clear_protocol_state(self) -> None:
        self._protocol_ready = False
        self._identity = None

    def _bootstrap(self) -> AutoWaveIdentity:
        self._protocol_ready = False
        identity = parse_autowave_identity(self._control_once("*IDN?"))
        self._control_once("*ECHO:ON")
        self._control_once("*PRCL:ON")
        self._identity = identity
        self._protocol_ready = True
        return identity

    def _control_once(self, command: str, *, timeout_s: float | None = None) -> str:
        self._validate_control_command(command)
        return self.client.query(command, timeout_s=timeout_s)

    @staticmethod
    def _validate_control_command(command: str) -> None:
        if not isinstance(command, str):
            raise AutoWaveValidationError(
                f"control command must be str, got {type(command).__name__}"
            )
        if not command.startswith("*"):
            raise AutoWaveValidationError("AutoWave control-plane transactions must begin with '*'")

    def _require_connected(self) -> None:
        if not self._session.is_connected:
            raise AutoWaveConnectionStateError("AutoWave transport is not connected")

    def _require_protocol_ready(self) -> None:
        if not self.protocol_ready:
            raise AutoWaveConnectionStateError(
                "AutoWave framed protocol is not ready; call open() successfully first"
            )

    def _transact_frame_with_busy(
        self,
        frame: bytes,
        *,
        replay_policy: ReplayPolicy,
        busy_policy: BusyPolicy,
        timeout_s: float | None,
    ) -> AutoWaveReply:
        busy_started_at: float | None = None
        attempt = 0

        while True:
            attempt += 1
            try:
                raw = self.client.transact_bytes(
                    frame,
                    _response_request(),
                    timeout_s=timeout_s,
                    replay_policy=replay_policy,
                )
            except TransportError:
                self._clear_protocol_state()
                raise
            reply = parse_reply(raw)
            if reply.kind is not AutoWaveReplyKind.BUSY:
                return raise_for_status(reply)

            if busy_started_at is None:
                busy_started_at = self._now()
            elapsed = self._now() - busy_started_at
            if (
                attempt >= busy_policy.attempts
                or elapsed + self._minimum_interval_s > busy_policy.max_elapsed_s
            ):
                raise AutoWaveBusyError(
                    "AutoWave remained BUSY after bounded exact-message re-query",
                    raw=reply.raw,
                    attempts=attempt,
                    elapsed_s=elapsed,
                )


def _validate_gpib_resource(resource_name: str) -> None:
    if not isinstance(resource_name, str) or not resource_name.strip():
        raise AutoWaveValidationError("VISA resource_name must be a non-empty string")
    normalized = resource_name.strip().upper()
    if not normalized.startswith("GPIB") or not normalized.endswith("::INSTR"):
        raise AutoWaveValidationError(
            "the initial AutoWave migration supports explicit GPIB ...::INSTR VISA resources"
        )


def _is_gpib_instr(resource_name: str) -> bool:
    normalized = resource_name.strip().upper()
    return normalized.startswith("GPIB") and normalized.endswith("::INSTR")


def discover_autowave_resources(
    resource_manager: Any,
    *,
    timeout_s: float = DEFAULT_DISCOVERY_TIMEOUT_S,
    resource_names: Iterable[str] | None = None,
) -> tuple[DiscoveredAutoWave, ...]:
    """Explicitly scan GPIB message resources with bounded, unframed *IDN?."""

    _validate_positive_finite(timeout_s, "timeout_s")
    names = (
        tuple(resource_manager.list_resources())
        if resource_names is None
        else tuple(resource_names)
    )
    found: list[DiscoveredAutoWave] = []

    for resource_name in names:
        if not _is_gpib_instr(resource_name):
            continue

        transport = VisaTransport(
            resource_name,
            timeout_s=float(timeout_s),
            resource_manager=resource_manager,
        )
        client = _build_client(
            transport,
            timeout_s=float(timeout_s),
            minimum_interval_s=0.0,
            sleep=time.sleep,
            now=time.monotonic,
        )
        try:
            transport.open()
            identity = parse_autowave_identity(client.query("*IDN?", timeout_s=float(timeout_s)))
        except ScpiDriverError:
            continue
        finally:
            with suppress(Exception):
                transport.close()
        found.append(DiscoveredAutoWave(resource_name=resource_name, identity=identity))

    return tuple(found)


def require_single_autowave(
    discovered: Iterable[DiscoveredAutoWave],
) -> DiscoveredAutoWave:
    """Require exactly one explicit discovery result; never silently choose."""

    matches = tuple(discovered)
    if not matches:
        raise AutoWaveDiscoveryError("no AutoWave instrument was discovered")
    if len(matches) > 1:
        resources = ", ".join(match.resource_name for match in matches)
        raise AutoWaveDiscoveryError(f"multiple AutoWave instruments discovered: {resources}")
    return matches[0]
