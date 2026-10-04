"""Characterize legacy high-level workflows and known defects."""

from __future__ import annotations

import pytest


def _interface_without_init(legacy_module):
    interface = legacy_module.com_interface.__new__(legacy_module.com_interface)
    interface.cmd = legacy_module.storage()
    interface.download_dir = None
    interface.start_time = None
    return interface


def test_legacy_run_test_file_sends_star_twice(
    legacy_module, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    interface = _interface_without_init(legacy_module)
    capsys.readouterr()
    calls: list[str] = []

    def pquery(command: str, *_args, **_kwargs) -> str:
        calls.append(command)
        if command == "DIR? DOWD":
            return "DIR DOWD:/home/guest/DowFiles"
        return command

    interface.pquery = pquery
    monkeypatch.setattr(legacy_module, "delay", lambda *_args, **_kwargs: None)

    interface.run_test_file("SineTest.dsg")
    capsys.readouterr()

    assert calls == [
        "DIR? DOWD",
        "SOUR SEGM SineTest.dsg",
        "TRIG:GEN 1",
        "STAR",
        "STAR",
    ]


def test_legacy_status_labels_duplicate_second_input(legacy_module, capsys) -> None:
    interface = _interface_without_init(legacy_module)
    capsys.readouterr()
    interface.pquery = lambda *_args, **_kwargs: "STAT TEST:0,0,0,0,0,0,0"

    status = interface.check_test_status()
    capsys.readouterr()

    assert status[4][0] == "IN 1:"
    assert status[5][0] == "IN 1:"


def test_legacy_get_test_time_falls_back_to_360_seconds_on_no_reply(
    legacy_module, capsys
) -> None:
    interface = _interface_without_init(legacy_module)
    capsys.readouterr()
    interface.pquery = lambda *_args, **_kwargs: None

    assert interface.get_test_time("missing.dsg", echo=False) == 360
    capsys.readouterr()


def test_legacy_reboot_is_sent_unframed_after_protocol_can_be_enabled(
    legacy_module, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    interface = _interface_without_init(legacy_module)
    capsys.readouterr()
    writes: list[str] = []

    class Instrument:
        def write(self, data: str) -> None:
            writes.append(data)

    interface.inst = Instrument()
    monkeypatch.setattr(legacy_module, "delay", lambda *_args, **_kwargs: None)

    interface.reboot()

    assert writes == ["REB"]


def test_legacy_typo_go_to_local_method_frames_star_command(
    legacy_module, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    interface = _interface_without_init(legacy_module)
    capsys.readouterr()
    writes: list[bytes] = []

    class Instrument:
        def write_raw(self, data: bytes) -> int:
            writes.append(data)
            return len(data)

    interface.inst = Instrument()
    monkeypatch.setattr(legacy_module, "delay", lambda *_args, **_kwargs: None)

    interface.got_to_local()

    assert writes == [
        bytes([0x02]) + b"*GTL" + bytes([0x03, legacy_module.str2check_sum("*GTL")])
    ]


@pytest.mark.parametrize(
    ("method_name", "expected_command"),
    [
        ("set_dc_voltage", "VSET:OUT1 13.5"),
        ("set_dc_offset", "VOFS:OUT1 0"),
    ],
)
def test_legacy_output_setters_write_without_consuming_protocol_reply(
    legacy_module,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
    method_name: str,
    expected_command: str,
) -> None:
    interface = _interface_without_init(legacy_module)
    capsys.readouterr()
    writes: list[bytes] = []
    reads = 0

    class Instrument:
        def write_raw(self, data: bytes) -> int:
            writes.append(data)
            return len(data)

        def read_raw(self) -> bytes:
            nonlocal reads
            reads += 1
            return b"\x06"

    interface.inst = Instrument()
    monkeypatch.setattr(legacy_module, "delay", lambda *_args, **_kwargs: None)

    getattr(interface, method_name)()

    expected = (
        bytes([0x02])
        + expected_command.encode("ascii")
        + bytes([0x03, legacy_module.str2check_sum(expected_command)])
    )
    assert writes == [expected]
    assert reads == 0


def test_legacy_initialization_sequence_sets_generator_mode(
    legacy_module, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    interface = _interface_without_init(legacy_module)
    capsys.readouterr()
    operations: list[tuple[str, str]] = []

    class Resource:
        write_termination = None
        timeout = None

        def set_visa_attribute(self, *_args) -> None:
            pass

        def query(self, command: str) -> str:
            operations.append(("query", command))
            return {
                "*IDN?": "*IDN:EM TEST, AutoWave, 0, 5.09.00, 4, 2",
                "*ECHO:ON": "*ECHO ON:OK",
                "*PRCL:ON": "*PRCL ON:OK",
            }[command]

    resource = Resource()

    class ResourceManager:
        def list_resources(self):
            return ("USB0::AutoWave::INSTR",)

        def open_resource(self, name: str):
            operations.append(("open", name))
            return resource

    interface.rm = ResourceManager()
    interface.inst = None

    def pquery(command: str, *_args, **_kwargs) -> str:
        operations.append(("pquery", command))
        return command

    interface.pquery = pquery
    monkeypatch.setattr(legacy_module, "delay", lambda *_args, **_kwargs: None)

    interface.init()
    capsys.readouterr()

    assert operations == [
        ("open", "USB0::AutoWave::INSTR"),
        ("query", "*IDN?"),
        ("query", "*ECHO:ON"),
        ("query", "*PRCL:ON"),
        ("pquery", "MOD GEN"),
    ]
