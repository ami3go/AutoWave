"""Typed public AutoWave driver API.

This layer maps device semantics onto the reviewed connection/session layer.
High-level multi-command workflows such as running a test file remain in PR05.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, Final

from scpi_driver_core.execution import RetryPolicy
from scpi_driver_core.transport import ReplayPolicy

import autowave.commands as commands
from autowave.connection import AutoWaveConnection
from autowave.errors import AutoWaveResponseError, AutoWaveValidationError
from autowave.models import (
    AutoWaveIdentity,
    DirectoryKind,
    GeneratorMode,
    TestStatus,
    TriggerMode,
)
from autowave.protocol import AutoWaveReplyKind, decode_payload_text

__all__ = ["AutoWave", "DEFAULT_SAFE_QUERY_RETRY_POLICY"]

DEFAULT_SAFE_QUERY_RETRY_POLICY: Final = RetryPolicy.constant(attempts=3, delay_s=0.25)


class AutoWave(AbstractContextManager["AutoWave"]):
    """Production-facing AutoWave driver built on the reviewed connection layer."""

    def __init__(
        self,
        connection: AutoWaveConnection,
        *,
        safe_query_retry_policy: RetryPolicy | None = DEFAULT_SAFE_QUERY_RETRY_POLICY,
    ) -> None:
        self._connection = connection
        self._safe_query_retry_policy = safe_query_retry_policy

    @classmethod
    def visa(
        cls,
        resource_name: str,
        *,
        alias: str = "autowave",
        timeout_s: float = 2.0,
        minimum_interval_s: float = 0.250,
        resource_manager: Any | None = None,
        visa_library: str = "",
        safe_query_retry_policy: RetryPolicy | None = DEFAULT_SAFE_QUERY_RETRY_POLICY,
    ) -> "AutoWave":
        return cls(
            AutoWaveConnection.visa(
                resource_name,
                alias=alias,
                timeout_s=timeout_s,
                minimum_interval_s=minimum_interval_s,
                resource_manager=resource_manager,
                visa_library=visa_library,
            ),
            safe_query_retry_policy=safe_query_retry_policy,
        )

    @property
    def connection(self) -> AutoWaveConnection:
        return self._connection

    @property
    def identity(self) -> AutoWaveIdentity | None:
        return self._connection.identity

    @property
    def is_connected(self) -> bool:
        return self._connection.is_connected

    @property
    def protocol_ready(self) -> bool:
        return self._connection.protocol_ready

    def open(self) -> AutoWaveIdentity:
        return self._connection.open()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "AutoWave":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # -- control-plane commands -----------------------------------------

    def reset(self) -> None:
        """Issue unframed *RST and close only after a confirmed write."""

        self._connection.control_write("*RST")
        self._connection.close()

    def go_to_local(self) -> None:
        """Issue vendor *GTL, which may stop a running test."""

        self._connection.control_write("*GTL")

    def set_echo_enabled(self, enabled: bool) -> str:
        return self._connection.set_echo_enabled(enabled)

    def set_protocol_enabled(self, enabled: bool) -> str:
        return self._connection.set_protocol_enabled(enabled)

    # -- framed side-effecting commands --------------------------------

    def set_generator_mode(self, mode: GeneratorMode) -> None:
        self._write_framed(commands.set_generator_mode(mode))

    def set_trigger_mode(self, mode: TriggerMode) -> None:
        self._write_framed(commands.set_trigger_mode(mode))

    def set_voltage(self, voltage: float, *, channel: int = 1) -> None:
        self._validate_installed_output(channel)
        self._write_framed(commands.set_voltage(channel, voltage))

    def set_offset(self, offset: float, *, channel: int = 1) -> None:
        self._validate_installed_output(channel)
        self._write_framed(commands.set_offset(channel, offset))

    def select_file(self, file_name: str) -> None:
        self._write_framed(commands.select_file(file_name))

    # -- safe framed queries --------------------------------------------

    def query_test_status(self) -> TestStatus:
        text = self._query_text(commands.status_test_query())
        payload = _parse_prefixed_value(text, "STAT TEST:")
        parts = [part.strip() for part in payload.split(",")]
        if len(parts) != 7:
            raise AutoWaveResponseError(
                f"expected 7 STAT TEST fields, got {len(parts)}: {text!r}",
                raw=text.encode("ascii", errors="replace"),
            )
        try:
            values = tuple(int(part, 10) for part in parts)
        except ValueError as exc:
            raise AutoWaveResponseError(
                f"STAT TEST contains a non-integer field: {text!r}",
                raw=text.encode("ascii", errors="replace"),
            ) from exc

        return TestStatus(
            test_state=values[0],
            output_states=(values[1], values[2], values[3], values[4]),
            input_states=(values[5], values[6]),
            raw=text,
        )

    def query_output_status(self, channel: int) -> int:
        self._validate_installed_output(channel)
        text = self._query_text(commands.status_output_query(channel))
        return _parse_int_value(text, f"STAT OUT{channel}:")

    def query_input_status(self, channel: int) -> int:
        self._validate_installed_input(channel)
        text = self._query_text(commands.status_input_query(channel))
        return _parse_int_value(text, f"STAT IN{channel}:")

    def query_system_status(self) -> str:
        return self._query_text(commands.status_system_query())

    def query_mac_address(self) -> str:
        text = self._query_text(commands.status_mac_query())
        return _parse_prefixed_value(text, "STAT MAC:").strip()

    def get_directory(self, kind: DirectoryKind) -> str:
        text = self._query_text(commands.directory_query(kind))
        return _parse_prefixed_value(text, f"DIR {kind.value}:").strip()

    def list_directory(self, path: str) -> str:
        return self._query_text(commands.list_directory(path))

    def query_file_details(self, file_name: str) -> str:
        return self._query_text(commands.file_details_query(file_name))

    def query_file_duration(self, file_name: str) -> str:
        return self._query_text(commands.file_duration_query(file_name))

    # -- internal helpers ------------------------------------------------

    def _write_framed(self, command: str) -> None:
        self._connection.transact_framed(
            command,
            replay_policy=ReplayPolicy.NEVER,
        )

    def _query_text(self, command: str) -> str:
        reply = self._connection.transact_framed(
            command,
            replay_policy=ReplayPolicy.SAFE,
            retry_policy=self._safe_query_retry_policy,
        )
        if reply.kind is not AutoWaveReplyKind.DATA:
            raise AutoWaveResponseError(
                f"expected decorated data reply for {command!r}, got {reply.kind.value}",
                raw=reply.raw,
            )
        return decode_payload_text(reply)

    def _validate_installed_output(self, channel: int) -> None:
        commands.status_output_query(channel)
        identity = self._connection.identity
        if identity is not None and identity.outputs is not None and channel > identity.outputs:
            raise AutoWaveValidationError(
                f"output channel {channel} exceeds installed output count {identity.outputs}"
            )

    def _validate_installed_input(self, channel: int) -> None:
        commands.status_input_query(channel)
        identity = self._connection.identity
        if identity is not None and identity.inputs is not None and channel > identity.inputs:
            raise AutoWaveValidationError(
                f"input channel {channel} exceeds installed input count {identity.inputs}"
            )


def _parse_prefixed_value(response: str, prefix: str) -> str:
    if not response.upper().startswith(prefix.upper()):
        raise AutoWaveResponseError(
            f"expected response prefix {prefix!r}, got {response!r}",
            raw=response.encode("ascii", errors="replace"),
        )
    return response[len(prefix) :]


def _parse_int_value(response: str, prefix: str) -> int:
    value = _parse_prefixed_value(response, prefix).strip()
    try:
        return int(value, 10)
    except ValueError as exc:
        raise AutoWaveResponseError(
            f"expected integer after {prefix!r}, got {response!r}",
            raw=response.encode("ascii", errors="replace"),
        ) from exc
