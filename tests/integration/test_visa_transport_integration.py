"""VisaTransport integration with an injected VISA resource manager.

PyVISA-sim cannot faithfully represent AutoWave's no-terminator GPIB END/EOI
profile, so this test exercises the real scpi-driver-core VisaTransport class
with a byte-preserving VISA resource double instead of adding fake line endings.
"""

from __future__ import annotations

from collections import deque

import pytest

from autowave.connection import AutoWaveConnection


class FakeVisaResource:
    def __init__(self, responses: list[bytes]) -> None:
        self.timeout = 0.0
        self.chunk_size = 0
        self._responses = deque(responses)
        self.writes: list[bytes] = []
        self.close_count = 0

    def write_raw(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def read_raw(self) -> bytes:
        if not self._responses:
            raise RuntimeError("no scripted VISA response")
        return self._responses.popleft()

    def close(self) -> None:
        self.close_count += 1


class FakeResourceManager:
    def __init__(self, resource: FakeVisaResource) -> None:
        self.resource = resource
        self.open_calls: list[tuple[str, dict[str, object]]] = []

    def open_resource(self, resource_name: str, **kwargs: object) -> FakeVisaResource:
        self.open_calls.append((resource_name, kwargs))
        return self.resource


@pytest.mark.integration
def test_connection_uses_real_visa_transport_without_text_terminators() -> None:
    resource = FakeVisaResource(
        [
            b"*IDN:EM TEST, AutoWave, 0, 8.03.02, 4, 2",
            b"*ECHO ON:OK",
            b"*PRCL ON:OK",
        ]
    )
    manager = FakeResourceManager(resource)

    connection = AutoWaveConnection.visa(
        "GPIB0::5::INSTR",
        timeout_s=1.0,
        minimum_interval_s=0.0,
        resource_manager=manager,
    )

    with connection as active:
        assert active.identity is not None
        assert active.identity.model == "AutoWave"
        assert active.identity.firmware_version == "8.03.02"
        assert active.protocol_ready is True

    assert resource.writes == [b"*IDN?", b"*ECHO:ON", b"*PRCL:ON"]
    assert resource.close_count == 1
    assert len(manager.open_calls) == 1
    name, kwargs = manager.open_calls[0]
    assert name == "GPIB0::5::INSTR"
    assert kwargs["read_termination"] is None
    assert kwargs["write_termination"] is None
    assert connection.is_connected is False
    assert connection.protocol_ready is False
