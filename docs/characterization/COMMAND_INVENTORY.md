# AutoWave command and replay inventory

**Baseline version:** 0.0.3  
**Reference:** EM Test AutoWave Remote Manual V6.02.02  
**Purpose:** define exactly what the current driver covers and how each operation may be retried

Legend:

- **safe-query** — may be retried only through the reviewed safe-query recovery path;
- **busy-only** — no generic replay; exact-message resend is allowed only after verified BUSY 0x19;
- **never** — do not automatically replay after uncertain outcome;
- **destructive-query** — query consumes device state and must not be automatically replayed.

## 1. Communication commands

| Operation | Manual syntax | Legacy path | Framing after protocol ON | Replay class | Disposition |
| --- | --- | --- | --- | --- | --- |
| Identify | `*IDN?` | `cmd.idn.req()` | always unframed | safe-query | migrate; normalize vendor prefix |
| Reset | `*RST` | command tree only | always unframed | never | expose explicitly; no automatic use |
| Go local | `*GTL` | `disconnect()`, `got_to_local()` | always unframed | never | preserve; document stop-test side effect; fix framed typo method |
| Echo ON/OFF | `*ECHO:<ON/OFF>` | command tree/init | always unframed | never | bootstrap operation |
| Echo query | `*ECHO?` | builder emits wrong `*ECHO:?` | always unframed | safe-query | fix syntax |
| Reboot | `REB` | `reboot()` | framed | never | legacy sends unframed; fix |
| License set | `LCN <key>` | not exposed | framed | never | outside initial migration API |
| License query | `LCN?` | not exposed | framed | safe-query | optional later feature |
| Protocol ON/OFF | `*PRCL:<ON/OFF>` | command tree/init | always unframed | never | bootstrap/control operation |
| Protocol query | `*PRCL?` | builder emits wrong `*PRCL:?` | always unframed | safe-query | fix syntax |

## 2. Test setup and execution

| Operation | Manual/verified syntax | Legacy path | Replay class | Disposition |
| --- | --- | --- | --- | --- |
| Mode generator | `MOD GEN` for first migration | `cmd.mode.gen` | busy-only | migrate |
| Mode recorder | `MOD REC` | `cmd.mode.rec` | busy-only | migrate only if compatibility requires |
| Mode gen+rec | `MOD GNRC` | `cmd.mode.gen_and_rec` | busy-only | migrate only if compatibility requires |
| Source segment file | `SOUR SEGM <file>` | `cmd.file.select` | busy-only | migrate |
| Set output voltage | `VSET:OUT1..4 <Voltage>` | `set_dc_voltage()` | busy-only | migrate; typed validation and consume reply |
| Set output offset | `VOFS:OUT1..4 <Voltage>` | `set_dc_offset()` | busy-only | migrate; typed validation and consume reply |
| Trigger generator | `TRIG:GEN <0..7>` | `cmd.trigGen.*` | busy-only | migrate |
| Start | `STAR` | `run_test_file()` | busy-only | migrate; send once |
| Stop | `STOP` | command tree only | busy-only | expose explicitly |
| Break | `BREA` | legacy emits `BREAK` | busy-only | fix syntax |
| Range | `RANG:...` | not implemented | never/busy-only | outside migration baseline |
| Events | `EVNT <Evnt>` | not implemented | never/busy-only | outside migration baseline |
| Trigger OUT/IN | `TRIG:OUTx`, `TRIG:IN2` | not implemented | never/busy-only | outside migration baseline |
| DUT monitor | `DUTM:INx`, `DUTM?:INx` | not implemented | set=never/query=safe-query | outside migration baseline |

For side-effecting framed commands, **busy-only** means the operation itself is never replayed
after timeout/transport uncertainty. The same encoded message may be sent again only when the
instrument explicitly returned BUSY as defined by the protocol.

## 3. Miscellaneous commands

| Operation | Syntax | Legacy path | Replay class | Disposition |
| --- | --- | --- | --- | --- |
| Display | `DISP <string>` | command tree only | busy-only | compatibility/future |
| Set date | `DAT <timestamp>` | command tree only | busy-only | compatibility/future |
| Read date | `DAT?` | command tree only | safe-query | compatibility/future |

## 4. File-control commands

Actual file payload transfer is not part of the command channel.

| Operation | Syntax | Legacy coverage | Replay class | Disposition |
| --- | --- | --- | --- | --- |
| Size | `SIZ? <filePath>` | yes | safe-query | migrate |
| Initialize download | `TRFL <filePath>` | builder only | busy-only | preserve if needed |
| Initialize upload | `TRFL? <filePath>` | builder only | safe-query only after HIL proves no destructive state transition; otherwise never | conservative until HIL |
| Delete | `DEL <filePath>` | builder only | never | do not auto-replay |
| Directory | `DIR? <dirPath>` | yes | safe-query | migrate |
| Download dir | `DIR? DOWD` | yes | safe-query | migrate |
| Record dir | `DIR? RECD` | yes | safe-query | migrate |
| Upgrade dir | `DIR? UPGD` | overwritten in legacy | safe-query | expose separately |
| Log dir | `DIR? LOGD` | survives as mislabeled `get_dir_upgrade` | safe-query | expose separately |
| File exists | `CKFL? <filePath>` | yes | safe-query | migrate |
| Test details | `CKLF? <FileName>` | yes | safe-query | migrate; HIL framing check |
| Total duration | `CKFD? <FileName>` | yes | safe-query | migrate |
| Save point header | `CKHD? <filePath.dpt>` | not implemented | not classified safe until verified | outside baseline |
| Log filename | `FLNM? DUTM/ERR` | not implemented | safe-query | outside baseline |

## 5. State/status commands

| Operation | Syntax | Legacy coverage | Replay class | Disposition |
| --- | --- | --- | --- | --- |
| Test state | `STAT? TEST` | yes | safe-query | migrate |
| Input state | `STAT? IN1/IN2` | yes | safe-query | migrate |
| Output state | `STAT? OUT1..4` | yes | safe-query | migrate |
| System state/version | `STAT? SYST` | yes | safe-query | migrate |
| Battery | `STAT? BATT` | no | safe-query | outside baseline |
| MAC | `STAT? MAC` | yes | safe-query | migrate |
| DUT monitor | `STAT? DUTM` | no | safe-query | outside baseline |
| Error | `STAT? ERR` | no | destructive-query | explicit API only; never hidden/automatic |
| DUT monitor level | `STAT:DUTM:INx?` | no | safe-query | outside baseline |
| Minimum latency | `STAT? DLTM` | no | safe-query | outside baseline |

## 6. Current command-string discrepancies

| Current legacy string/behavior | Verified target |
| --- | --- |
| `BREAK` | `BREA` |
| `*ECHO:?` | `*ECHO?` |
| `*PRCL:?` | `*PRCL?` |
| UPGD accessor resolves to `DIR? LOGD` | separate `DIR? UPGD` and `DIR? LOGD` |
| `REB` sent via unframed `send()` after protocol enable | framed command transaction |
| `*GTL` sent through framed `psend()` by `got_to_local()` | always unframed |
| VSET/VOFS use write-only `psend()` | framed transaction that consumes reply |
| `STAR` sent twice by `run_test_file()` | one `STAR` |

## 7. Scope rule

Commands documented by the manual but absent from the legacy API are recorded above so the
migration does not accidentally imply full-manual coverage. PR00-PR08 prioritize migrating and
hardening the existing operational surface. Additional command families require separate
feature work unless a migrated workflow depends on them.
