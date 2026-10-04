# Public AutoWave driver API

Version 0.4.0 introduces the typed public driver surface in `autowave.driver`.
The API is intentionally explicit: command semantics live in driver methods,
wire framing remains in `autowave.protocol`, and transport/session behavior
remains in `autowave.connection`.

High-level multi-command workflows such as starting/stopping a complete test
sequence are intentionally deferred to PR05.

## Basic connection

```python
from autowave import AutoWave

with AutoWave.visa("GPIB0::5::INSTR") as aw:
    print(aw.identity)
```

Opening performs only the communication bootstrap:

```text
*IDN?
*ECHO:ON
*PRCL:ON
```

It does not automatically select generator mode or change output state.

## Typed modes

```python
from autowave import GeneratorMode, TriggerMode

aw.set_generator_mode(GeneratorMode.GENERATOR)
aw.set_trigger_mode(TriggerMode.MANUAL_START)
```

The driver uses enums rather than exposing numeric/mnemonic magic values at
the public API.

## Output voltage and offset

```python
aw.set_voltage(13.5, channel=1)
aw.set_offset(-5.0, channel=1)
```

Validation is strict:

- output channels are limited to 1..4 by the protocol;
- when identity reports fewer installed outputs, the installed count is also enforced;
- voltage range is 0..60 V;
- offset range is -60..60 V;
- NaN and infinity are rejected;
- invalid values raise `AutoWaveValidationError`;
- values are never silently clamped.

The signed offset behavior deliberately fixes the legacy defect where a valid
negative offset was accepted by one layer and then clamped to zero by another.

## Status queries

```python
status = aw.query_test_status()
print(status.test_state)
print(status.output_states)
print(status.input_states)

out1 = aw.query_output_status(1)
in1 = aw.query_input_status(1)
system = aw.query_system_status()
mac = aw.query_mac_address()
```

`query_test_status()` returns a typed `TestStatus` rather than the legacy
nested list. It preserves the raw response as well.

Input status is limited to channels 1..2, and the identity-reported installed
input count is enforced when available.

## Files and directories

```python
from autowave import DirectoryKind

download_dir = aw.get_directory(DirectoryKind.DOWNLOAD)
upgrade_dir = aw.get_directory(DirectoryKind.UPGRADE)
log_dir = aw.get_directory(DirectoryKind.LOG)

listing = aw.list_directory(download_dir)
exists_response = aw.query_file_exists(f"{download_dir}/test.dsg")
details = aw.query_file_details("test.dsg")
duration = aw.query_file_duration("test.dsg")

aw.select_file("test.dsg")
```

Upgrade and log directories are separate. This fixes the legacy command-tree
bug where the UPGD accessor was overwritten with LOGD.

The current metadata methods return the validated/raw device text where the
vendor manual does not define enough stable structure for a stronger typed
model. PR05 may add higher-level parsers only where the protocol evidence is
clear.

Actual file payload transfer is not performed by these command methods.

## Local control and reset

```python
aw.go_to_local()
aw.reset()
```

`go_to_local()` sends vendor `*GTL`. The AutoWave manual states that this
can stop a running test, so it is treated as a physical side effect and is
never automatically replayed.

`reset()` sends `*RST` as an unframed write and closes the session after
the confirmed write. If the write outcome is uncertain, it is not retried.

## Echo and protocol control

```python
aw.set_echo_enabled(False)
aw.set_protocol_enabled(False)
aw.set_protocol_enabled(True)
```

These are unframed vendor control-plane commands. Protocol enable/disable also
updates the connection's cached `protocol_ready` state so framed commands
cannot be issued while protocol mode is knowingly disabled.

## Retry classification

Public driver methods deliberately separate safe queries from side effects.

Side-effecting methods use `ReplayPolicy.NEVER`:

- generator mode;
- trigger mode;
- voltage;
- offset;
- file selection;
- reset/local-control writes.

Read-only framed queries use `ReplayPolicy.SAFE` and, by default, a bounded
three-attempt retry policy with 250 ms delay between attempts. On a transport
fault, the connection reopens and re-runs communication bootstrap before a
safe query can be replayed.

Vendor BUSY handling remains separate from generic retry and is governed by the
bounded BUSY policy in the connection layer.

## Response validation

Queries that require decorated data reject ACK-only replies instead of
inventing an empty/default value.

Typed parsers reject:

- wrong response prefixes;
- wrong field counts;
- non-integer status fields;
- malformed or non-ASCII protocol payloads.

## Command injection protection

String arguments used for file/path commands reject CR and LF. One public
method call therefore cannot inject a second physical command through a line
break.

## Legacy compatibility

The old top-level modules remain installable during the migration:

```python
import AutoWave_class
import Timer_class
```

PR04 does not yet redirect `com_interface` to the new driver. The legacy
facade is handled only where it can be done without reintroducing unsafe retry,
clamping, or protocol behavior. Operational workflow compatibility is reviewed
in PR05.

## Not part of PR04

PR04 intentionally does not implement the multi-command workflows for:

- run test file;
- start;
- stop;
- break;
- reboot;
- bounded test-state polling;
- transfer initialization.

Those operations are PR05 because they need workflow-level side-effect,
timeout, and partial-failure review rather than being mixed into the command
API phase.
