"""Exact command construction produced by the legacy command tree."""

from __future__ import annotations


def test_legacy_core_command_strings(legacy_module, capsys) -> None:
    cmd = legacy_module.storage()
    capsys.readouterr()  # legacy status constructor prints during initialization

    assert cmd.idn.req() == "*IDN?"
    assert cmd.reset.str() == "*RST"
    assert cmd.go_to_local.str() == "*GTL"
    assert cmd.echo.on.str() == "*ECHO:ON"
    assert cmd.echo.off.str() == "*ECHO:OFF"
    assert cmd.protocol.on.str() == "*PRCL:ON"
    assert cmd.protocol.off.str() == "*PRCL:OFF"
    assert cmd.reboot.str() == "REB"

    assert cmd.mode.gen.str() == "MOD GEN"
    assert cmd.mode.rec.str() == "MOD REC"
    assert cmd.mode.gen_and_rec.str() == "MOD GNRC"

    assert cmd.start_test.str() == "STAR"
    assert cmd.stop_test.str() == "STOP"
    # Known legacy/manual discrepancy: target command is BREA.
    assert cmd.break_test.str() == "BREAK"

    assert cmd.trigGen.off.str() == "TRIG:GEN 0"
    assert cmd.trigGen.manual_start.str() == "TRIG:GEN 1"
    assert cmd.trigGen.trigIn_start.str() == "TRIG:GEN 2"
    assert cmd.trigGen.auto.str() == "TRIG:GEN 3"
    assert cmd.trigGen.manual_event.str() == "TRIG:GEN 4"
    assert cmd.trigGen.trigIn_event.str() == "TRIG:GEN 5"
    assert cmd.trigGen.manual_iter.str() == "TRIG:GEN 6"
    assert cmd.trigGen.trigIn_iter.str() == "TRIG:GEN 7"


def test_legacy_query_builder_adds_question_mark_after_colon(legacy_module, capsys) -> None:
    """Characterize an unused but incorrect query-builder result."""

    cmd = legacy_module.storage()
    capsys.readouterr()

    assert cmd.echo.req() == "*ECHO:?"
    assert cmd.protocol.req() == "*PRCL:?"


def test_legacy_voltage_and_offset_commands(legacy_module, capsys) -> None:
    cmd = legacy_module.storage()
    capsys.readouterr()

    assert cmd.setVoltage.out1.val(13.5) == "VSET:OUT1 13.5"
    assert cmd.setVoltage.out4.val(0) == "VSET:OUT4 0"
    assert cmd.setOffset.out1.val(-5) == "VOFS:OUT1 -5"
    assert cmd.setOffset.out4.val(5) == "VOFS:OUT4 5"


def test_legacy_file_command_strings(legacy_module, capsys) -> None:
    cmd = legacy_module.storage()
    capsys.readouterr()

    assert cmd.file.get_file_list.path("/home/guest/DowFiles") == "DIR? /home/guest/DowFiles"
    assert cmd.file.get_dir_download.str() == "DIR? DOWD"
    assert cmd.file.get_dir_record.str() == "DIR? RECD"

    # Known defect: UPGD is created and immediately overwritten by LOGD.
    assert cmd.file.get_dir_upgrade.str() == "DIR? LOGD"

    assert cmd.file.get_file_size.path("/tmp/a.dsg") == "SIZ? /tmp/a.dsg"
    assert cmd.file.TRLF.path("/tmp/a.dsg") == "TRFL /tmp/a.dsg"
    assert cmd.file.TRLF_req.path("/tmp/a.dsg") == "TRFL? /tmp/a.dsg"
    assert cmd.file.check_file_exist.path("/tmp/a.dsg") == "CKFL? /tmp/a.dsg"
    assert cmd.file.check_details.path("a.dsg") == "CKLF? a.dsg"
    assert cmd.file.check_total_duration.path("a.dsg") == "CKFD? a.dsg"
    assert cmd.file.select.path("a.dsg") == "SOUR SEGM a.dsg"


def test_legacy_status_command_strings(legacy_module, capsys) -> None:
    cmd = legacy_module.storage()
    capsys.readouterr()

    assert cmd.status.sys_ver.str() == "STAT? SYST"
    assert cmd.status.read_mac.str() == "STAT? MAC"
    assert cmd.status.read_out1_status.str() == "STAT? OUT1"
    assert cmd.status.read_out4_status.str() == "STAT? OUT4"
    assert cmd.status.read_in1_status.str() == "STAT? IN1"
    assert cmd.status.read_in2_status.str() == "STAT? IN2"
    assert cmd.status.read_test_status.str() == "STAT? TEST"
