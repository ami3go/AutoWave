# PR00 — Legacy characterization baseline

**Repository version:** 0.0.3  
**Purpose:** freeze the behavior of the pre-migration driver before changing runtime architecture  
**Legacy runtime file:** `src/AutoWave_class.py`  
**Verified target protocol:** `docs/AUTOWAVE_PROTOCOL_BASELINE.md`

## 1. Scope

PR00 is intentionally non-invasive. It does not migrate transport ownership, protocol handling,
retry policy, packaging, or the public API. Its job is to make the current behavior explicit and
testable so later changes can distinguish compatibility from defect correction.

The baseline uses three evidence classes:

1. official AutoWave remote manual requirements;
2. executable characterization of the current driver;
3. explicit disposition for differences between the two.

The current implementation is not automatically treated as correct. A characterization test can
therefore lock down a known defect so that the migration has objective evidence of what is being
changed.

## 2. Current public surface

### Module-level functions

| Symbol | Current role | Migration disposition |
| --- | --- | --- |
| `delay(time_in_sec=0.25)` | blocking sleep helper | internal legacy helper; replace with bounded/paced core mechanisms |
| `range_check(val, min, max, val_name)` | silently clamps values | do not preserve; target raises typed validation errors |
| `str2dec_array(txt)` | converts text to ordinal-byte values | protocol implementation detail |
| `dec_array2check_sum(dec_array)` | legacy checksum | preserve verified algorithm in new protocol module |
| `str2check_sum(txt)` | text checksum wrapper | preserve behavior for ASCII vectors, replace implementation |

### Public/externally reachable classes

| Symbol | Current role | Migration disposition |
| --- | --- | --- |
| `com_interface` | connection, protocol, workflows and public driver API mixed together | compatibility facade only; replace internally with layered driver |
| `storage` | command-tree root | replace with explicit/auditable command methods/constants |
| `req3`, `str3`, `req_on_off`, `dig_param3`, `str_param3` | generic string-builder helpers | internal legacy API; do not carry forward unless real callers require compatibility |
| `mode`, `trig_gen`, `set_voltage`, `file`, `status` | command-tree groups | replace with typed driver methods and small explicit helpers |

### `com_interface` methods

| Method | Current behavior | Compatibility classification |
| --- | --- | --- |
| `init()` | discovers by resource-name substring, opens VISA, enables echo/protocol and sets generator mode | preserve via compatibility layer with corrected discovery/bootstrap separation |
| `send(txt)` | unframed VISA write + sleep | internal/compatibility only |
| `query(cmd_str)` | unframed VISA query with broad 10-attempt retry | intentional breaking fix |
| `psend(txt_cmd)` | framed raw write only | internal legacy helper; target framed operations transact and consume replies |
| `pquery(cmd_str, err_check=False, p_check=True)` | framed write/read with broad retry and ad-hoc parsing | replace |
| `close()` | closes VISA resource | preserve public intent using deterministic core close |
| `run_test_file(file_name)` | select file, trigger manual, sends STAR twice | preserve intent; correct duplicate STAR |
| `get_test_time(file_name, echo=True)` | parses CKLF; returns fake 360 s when no response | preserve intent; remove fake fallback |
| `check_test_status()` | parses STAT? TEST into nested list | preserve useful data, correct IN2 label and introduce typed model if compatible |
| `disconnect()` | sends unframed vendor `*GTL` | preserve semantics and document that it stops a running test |
| `reboot()` | sends unframed `REB` even after protocol enable | intentional protocol fix |
| `set_dc_voltage(volt=13.5, ch=1)` | clamps inputs and framed-write-only VSET | preserve intent; typed validation + consume protocol response |
| `set_dc_offset(volt=0, ch=1)` | clamps inputs and framed-write-only VOFS | preserve intent; typed validation + consume protocol response |
| `got_to_local()` | typo-named method that incorrectly frames `*GTL` | preserve temporarily as deprecated alias only; implementation must call correct unframed path |

## 3. Current initialization sequence

Executable characterization freezes the current sequence as:

```text
discover resource whose VISA name contains "AutoWave"
open resource
*IDN?          ordinary VISA query
*ECHO:ON       ordinary VISA query
*PRCL:ON       ordinary VISA query
MOD GEN        framed pquery
```

Target migration deliberately separates communication bootstrap from application state:

```text
open explicit resource
*IDN?
*ECHO:ON
*PRCL:ON
---- communication is ready ----
MOD GEN only when a workflow explicitly requires generator mode
```

Generator mode must not be automatically restored during transport recovery.

## 4. Current retry/error behavior

### Ordinary `query()`

- attempts to retry up to 10 times;
- catches every `Exception`;
- sleeps 5 s after errors;
- references `return_str` before assignment if the first VISA query raises;
- the resulting `UnboundLocalError` can mask the original transport failure.

### Framed `pquery()`

- retries all exceptions up to 10 times;
- treats BUSY, NOTREADY and NAK by raising generic exceptions into the same retry loop;
- has no explicit ACK-success path;
- falls through and returns `None` after retry exhaustion;
- does not distinguish safe query replay from physical side effects.

The target behavior is specified in `AUTOWAVE_PROTOCOL_BASELINE.md`: only a verified BUSY byte
permits bounded resend of the exact same message. Transport timeout, NAK, NOTREADY, checksum
failure and malformed framing do not authorize replay of side-effecting operations.

## 5. Known legacy defects frozen by tests

| ID | Current behavior | Target disposition |
| --- | --- | --- |
| LEG-001 | `query()` can mask the original exception with `UnboundLocalError` | fix; preserve original typed failure |
| LEG-002 | simple protocol replies ACK/NAK/NOTREADY/BUSY all fail to complete cleanly | implement typed simple-reply handling |
| LEG-003 | retry exhaustion can return `None` | raise typed terminal error |
| LEG-004 | `run_test_file()` sends `STAR` twice | send once |
| LEG-005 | break command is `BREAK` | use documented `BREA` |
| LEG-006 | second status input is labeled IN1 | label IN2 |
| LEG-007 | UPGD directory command is overwritten by LOGD | expose both independently |
| LEG-008 | `*ECHO?` builder emits `*ECHO:?` | correct query syntax |
| LEG-009 | `*PRCL?` builder emits `*PRCL:?` | correct query syntax |
| LEG-010 | invalid numeric input is silently clamped | reject with typed validation error |
| LEG-011 | `get_test_time()` returns invented 360 s on communication failure | remove fallback |
| LEG-012 | `reboot()` sends non-star `REB` unframed after protocol can be ON | use framed transaction when protocol is active |
| LEG-013 | `got_to_local()` frames a star command even though star commands are never framed | deprecated alias must use unframed `*GTL` |
| LEG-014 | VSET/VOFS helpers write frames without reading the protocol response | transact and consume ACK/decorated response |
| LEG-015 | discovery depends on the text "AutoWave" appearing in the VISA resource name | explicit resource first; bounded IDN-based discovery optional |
| LEG-016 | constructor/status path emits diagnostic `print()` output | replace with structured diagnostics or silence |
| LEG-017 | `pquery(err_check=True)` searches response text for `:ERR` instead of typed protocol/device status | replace with explicit response semantics |
| LEG-018 | `disconnect()` name hides the fact that `*GTL` stops a running test | document side effect; provide clearer new API |

## 6. Compatibility policy

The preferred new API will be explicit and typed. Legacy compatibility should be provided only
where it does not preserve unsafe behavior.

Rules:

- valid method intent is preserved where practical;
- unsafe retries, silent clamping, fabricated fallback values and protocol violations are not
  compatibility requirements;
- typo `got_to_local()` may remain temporarily as a deprecation alias;
- legacy nested-list status output may be retained by a compatibility adapter while the new API
  uses a typed result;
- legacy command-builder helper classes are not guaranteed public API unless an external caller
  is found in repository/user code;
- all intentional behavior changes must appear in the migration guide/changelog.

## 7. PR00 executable evidence

The characterization suite verifies:

- official checksum vectors;
- checksum raw-0x20 boundary behavior;
- exact framed bytes for a representative command;
- decorated response parsing;
- current handling of all one-byte protocol replies;
- exact legacy command strings;
- legacy query-builder syntax defects;
- duplicate `STAR`;
- duplicated IN1 status label;
- 360 s fabricated fallback;
- unframed reboot behavior;
- incorrectly framed `*GTL`;
- write-without-read VSET/VOFS behavior;
- current initialization sequence;
- exception masking;
- silent range clamping.

These tests must stay separated under `tests/characterization/` so later target-behavior tests
are not confused with intentional snapshots of legacy defects.

## 8. Exit gate

PR00 is complete when:

- every current command path used by the legacy workflows is inventoried;
- every known discrepancy has an explicit disposition;
- side-effect/replay classification exists;
- HIL unknowns are listed;
- characterization tests pass without physical hardware or PyVISA;
- no runtime source behavior has been modified;
- version is 0.0.3;
- the PR has been reviewed and no P0/P1 planning finding remains.
