"""VISA discovery tests using an injected resource manager."""

from __future__ import annotations

from collections import deque

import pytest

from autowave.connection import discover_autowave_resources, require_single_autowave
from autowave.errors import AutoWaveDiscoveryError, AutoWaveValidationError


class FakeVisaResource:
    def __init__(self, responses: list[bytes | Exception]) -> None:
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
            raise RuntimeError("no scripted response")
        response = self._responses.popleft()
        if isinstance(response, Exception):
            raise response
        return response

    def close(self) -> None:
        self.close_count += 1


class FakeResourceManager:
    def __init__(self, resources: dict[str, FakeVisaResource]) -> None:
        self.resources = resources
        self.list_calls = 0
        self.opened: list[str] = []

    def list_resources(self) -> tuple[str, ...]:
        self.list_calls += 1
        return tuple(self.resources)

    def open_resource(self, resource_name: str, **_kwargs: object) -> FakeVisaResource:
        self.opened.append(resource_name)
        return self.resources[resource_name]


def test_discovery_queries_only_gpib_instr_candidates_and_closes_every_resource() -> None:
    aw = FakeVisaResource([b"*IDN:EM TEST, AutoWave, 0, 5.10.08, 4, 2"])
    other = FakeVisaResource([b"OTHER,DMM,SN1,1.0"])
    tcp = FakeVisaResource([b"*IDN:EM TEST, AutoWave, 0, 5.10.08, 4, 2"])
    manager = FakeResourceManager(
        {
            "GPIB0::5::INSTR": aw,
            "GPIB0::6::INSTR": other,
            "TCPIP0::192.0.2.10::INSTR": tcp,
        }
    )

    found = discover_autowave_resources(manager, timeout_s=0.2)

    assert [item.resource_name for item in found] == ["GPIB0::5::INSTR"]
    assert aw.writes == [b"*IDN?"]
    assert other.writes == [b"*IDN?"]
    assert tcp.writes == []
    assert aw.close_count == 1
    assert other.close_count == 1
    assert tcp.close_count == 0
    assert manager.list_calls == 1


def test_discovery_explicit_resource_names_do_not_enumerate_manager() -> None:
    aw = FakeVisaResource([b"EM TEST,AutoWave,SN42,8.03.02,4,2"])
    ignored = FakeVisaResource([b"EM TEST,AutoWave,SN43,8.03.02,4,2"])
    manager = FakeResourceManager(
        {
            "GPIB0::5::INSTR": aw,
            "GPIB0::6::INSTR": ignored,
        }
    )

    found = discover_autowave_resources(
        manager,
        timeout_s=0.2,
        resource_names=["GPIB0::5::INSTR"],
    )

    assert len(found) == 1
    assert found[0].identity.serial_number == "SN42"
    assert manager.list_calls == 0
    assert manager.opened == ["GPIB0::5::INSTR"]
    assert aw.close_count == 1
    assert ignored.close_count == 0


def test_discovery_ignores_unresponsive_or_non_autowave_candidates() -> None:
    broken = FakeVisaResource([RuntimeError("backend read failure")])
    malformed = FakeVisaResource([b"EM TEST,Other,SN1,1.0"])
    manager = FakeResourceManager(
        {
            "GPIB0::4::INSTR": broken,
            "GPIB0::5::INSTR": malformed,
        }
    )

    assert discover_autowave_resources(manager, timeout_s=0.2) == ()
    assert broken.close_count == 1
    assert malformed.close_count == 1


@pytest.mark.parametrize("timeout", [0.0, -1.0, float("inf"), True])
def test_discovery_requires_positive_finite_timeout(timeout: float) -> None:
    manager = FakeResourceManager({})
    with pytest.raises(AutoWaveValidationError):
        discover_autowave_resources(manager, timeout_s=timeout)


def test_require_single_discovery_reports_ambiguity_without_selecting() -> None:
    first_resource = FakeVisaResource([b"EM TEST,AutoWave,SN1,1.0"])
    second_resource = FakeVisaResource([b"EM TEST,AutoWave,SN2,1.0"])
    manager = FakeResourceManager(
        {
            "GPIB0::5::INSTR": first_resource,
            "GPIB0::6::INSTR": second_resource,
        }
    )

    found = discover_autowave_resources(manager, timeout_s=0.2)
    assert len(found) == 2

    with pytest.raises(AutoWaveDiscoveryError, match="multiple"):
        require_single_autowave(found)
