# AutoWave verified protocol baseline

**Document status:** mandatory implementation input  
**AutoWave repository version:** 0.0.2  
**Primary protocol reference:** EM Test, *AutoWave Manual for Remote Control*, V 6.02.02, 8 Dec 2020  
**Migration core baseline:** scpi-driver-core 0.1.0.dev6 at `d850f88a78ddfbfa08b667c0be6cbb0bb4a01541`

## 1. Purpose

This document resolves the protocol, transport, timing, recovery, and compatibility ambiguities identified during the pre-coding review of the scpi-driver-core migration plan.

A code agent must treat the decisions in this document as part of the migration specification. Runtime migration code must not start by re-deciding these points.

## 2. Source of truth and precedence

The primary external reference is:

- EM Test, *Manual for Remote Control — AutoWave*, V 6.02.02, 8.12.2020.
- Source PDF: https://transientspecialists.com/cdn/shop/files/Remote_Manual_AutoWave_10e63ba6-5d51-42e4-bef3-eff3d2556cdb.pdf

Evidence precedence is:

1. explicit protocol/command definition in the official remote manual;
2. verified HIL traffic from the target AutoWave;
3. examples in the official remote manual;
4. current legacy driver behavior;
5. comments in the current legacy source.

If two sections of the official manual contradict each other, preserve the proven legacy behavior when it is consistent with at least one manual section and add a HIL assertion for the ambiguity. Do not silently choose a new syntax.

The manual states that the documented commands apply to firmware 8.03.02 or higher, while examples in the same document show lower firmware values. Therefore the new driver must record firmware and expose it, but must not reject a unit solely because its firmware string is below 8.03.02 until HIL demonstrates that such a gate is correct.

## 3. Migration scope

The production migration target is the existing GPIB/IEEE-488 driver path.

Primary transport:

```text
GPIB resource -> VisaTransport -> ScpiClient/ScpiSession -> AutoWave protocol
```

The manual also documents Ethernet/TCP port 15000. TCP support is architecturally permitted later, but it is not required for the first production migration and must not expand PR00-PR08 scope unless explicitly approved.

## 4. Verified IEEE-488 and timing baseline

The manual specifies:

- IEEE-488 addresses 1 through 30;
- IEEE-488-1975 interface;
- minimum 250 ms delay between two commands;
- a response to a request is normally expected within 300 ms.

Implementation decisions:

- keep the legacy-compatible VISA operation timeout at **2.0 s** initially;
- enforce a **minimum 0.250 s inter-command interval**;
- interpret the 250 ms requirement conservatively as a minimum interval after completion of one command transaction before the next outbound command begins;
- do **not** insert an artificial 250 ms sleep between the write and read halves of one request/response transaction;
- read the response immediately after writing;
- retain the manual's <300 ms response expectation as a diagnostic/HIL criterion, not as the initial hard timeout;
- HIL may justify reducing the 2.0 s timeout in a later reviewed PR.

Use the core pacing mechanism for ordinary commands. BUSY re-queries are also commands and must obey the same 250 ms pacing requirement.

## 5. Protocol state machine

The manual establishes three critical rules:

1. protocol mode is OFF when the equipment is switched on;
2. `*PRCL:<ON/OFF>` changes protocol mode;
3. **all commands whose first character is `*` are never framed**, even when protocol mode is ON.

The driver state model is therefore:

```text
DISCONNECTED
    |
    v
VISA OPEN
    |
    v
UNFRAMED CONTROL PLANE
    |  *IDN?
    |  *ECHO:ON
    |  *PRCL:ON
    v
FRAMED DEVICE PROTOCOL READY
    |
    +-- "*" commands remain unframed
    |
    +-- non-"*" commands use STX + payload + ETX + checksum
```

Canonical bootstrap sequence:

1. open VISA transport;
2. send unframed `*IDN?`;
3. validate that the reply identifies an AutoWave;
4. send unframed `*ECHO:ON`;
5. send unframed `*PRCL:ON`;
6. mark framed protocol ready.

Do **not** automatically set `MOD GEN` as part of communication recovery. Generator mode is application/device state and must be set explicitly by the workflow that requires it.

## 6. Unframed command transport configuration

For GPIB `::INSTR` resources use backend message boundaries/EOI.

The unframed control-plane client must be equivalent to:

```text
encoding: ASCII
command terminator: none
response terminator: none
maximum command size: 4096 bytes
maximum response size: 65536 bytes
default operation timeout: 2.0 s
minimum interval: 0.250 s
```

Do not append LF/CR to GPIB commands unless HIL proves that the target firmware requires it.

## 7. Framed protocol format

For every non-`*` command after protocol enable:

```text
STX + command payload + ETX + checksum
```

Control bytes:

| Meaning | Value |
| --- | ---: |
| STX | 0x02 |
| ETX | 0x03 |
| ACK | 0x06 |
| NAK | 0x15 |
| NOTREADY | 0x16 |
| BUSY | 0x19 |

Initial migration bounds:

- maximum command payload: **4096 bytes**;
- maximum complete response/message: **65536 bytes**.

These are defensive software bounds, not claims about the instrument's physical maximum.

The manual describes command bytes as IBM-PC characters from 0x20 through 0xFF. The exact glyph/code-page mapping above ASCII is not specified. Therefore:

- protocol framing/parsing must operate on bytes;
- the initial public string command API supports ASCII command text;
- do not use UTF-8 as a transparent replacement for the documented single-byte protocol;
- extended 0x80-0xFF text is out of scope until its character mapping is verified;
- binary framing code must not corrupt bytes solely because they are above 0x7F.

## 8. Checksum rule

Checksum calculation:

1. sum command payload bytes between STX and ETX;
2. apply `sum & 0xFF`;
3. if the resulting byte is **<= 0x20**, add `0x20`;
4. append the resulting byte after ETX.

Use `<= 0x20` because the dedicated checksum section of the manual states that rule and the legacy implementation uses it. Another sentence in the manual describes the threshold as <= 0x1F; this inconsistency must be captured by a test for a raw checksum of exactly 0x20 and verified during HIL.

Required known vectors from the manual:

```text
STAT? PSRC -> checksum 0xD3
LCN?       -> checksum 0x3C
```

## 9. Response classes and retry semantics

### 9.1 ACK — 0x06

ACK means the command was understood and treated.

For a command whose contract expects a simple acknowledgement, ACK is success.

Do not feed a one-byte ACK into decorated-frame parsing.

### 9.2 NAK — 0x15

NAK means the command was not understood or the checksum was wrong.

Behavior:

- raise `AutoWaveNakError`;
- do not automatically replay;
- record command/operation context without logging sensitive payloads;
- a deterministic locally generated bad checksum is a software defect and must fail tests rather than be hidden by retry.

### 9.3 NOTREADY — 0x16

NOTREADY means the command was not accepted. The manual additionally states that sending a new command while a prior command is still being treated can cause the prior command to be flushed, and further requests may remain NOTREADY until that flush completes.

Behavior:

- raise `AutoWaveNotReadyError`;
- do not automatically replay the rejected operation;
- never send a different command merely to probe around NOTREADY;
- a high-level workflow may perform a separately specified bounded recovery/wait procedure only when the device semantics are known.

### 9.4 BUSY — 0x19

BUSY is special. The manual explicitly instructs the caller to resend the **same previous message**, because the instrument cannot spontaneously report completion.

This is vendor-protocol polling, not generic transport retry.

Allowed behavior:

- resend only the exact same encoded frame;
- only after a verified BUSY byte was received;
- obey 250 ms pacing;
- default maximum attempts: **10 total sends**;
- default maximum elapsed BUSY handling: **5.0 s**;
- whichever bound is reached first terminates the operation with `AutoWaveBusyError`.

BUSY resend is allowed even for an operation that has a physical side effect because the device protocol explicitly defines the repeated identical request as the mechanism for obtaining completion.

BUSY handling must **not** be triggered by:

- transport timeout;
- missing response;
- malformed response;
- checksum error;
- NAK;
- NOTREADY;
- generic exception.

### 9.5 Decorated response

A decorated response is:

```text
STX + response payload + ETX + checksum
```

It is equivalent to ACK only after STX, ETX, bounds, checksum, and payload decoding have all passed validation.

Malformed or truncated framing must be treated as protocol failure and must not be silently retried.

## 10. Safe retry classification

The generic rule remains: do not replay physical operations after an uncertain transport outcome.

Examples that must not receive automatic transport retry:

- `STAR`;
- `STOP`;
- `BREA`;
- `TRIG:GEN ...`;
- `VSET...`;
- `VOFS...`;
- file selection;
- transfer initialization;
- reset/reboot;
- mode changes.

A safe query may opt into core retry only if:

1. it has no device-side state change;
2. it is explicitly classified safe;
3. recovery restores AutoWave protocol bootstrap before the query is replayed.

BUSY handling from section 9.4 is the only protocol-defined resend exception and is separate from `ReplayPolicy`.

## 11. Recovery contract

An uncertain transport failure faults the transport. The failed operation is not automatically replayed unless it was explicitly a safe query.

Driver-level recovery must:

1. call the core session recovery/open mechanism;
2. send/validate unframed `*IDN?`;
3. reissue unframed `*ECHO:ON`;
4. reissue unframed `*PRCL:ON`;
5. return to protocol-ready state;
6. **not** restore generator mode, selected file, trigger mode, voltage, offset, or a running test automatically.

For a safe-query retry, `before_retry` must call an AutoWave recovery callback that performs both core transport recovery and this bootstrap. Do not pass bare `ScpiSession.recover_if_faulted` when framed protocol state is required.

For a side-effecting operation whose outcome is uncertain:

- raise the transport/protocol error;
- allow explicit recovery;
- do not replay the operation after recovery.

## 12. Identity handling and discovery

The manual example returns an identification string with an AutoWave-specific prefix similar to:

```text
*IDN:EM TEST, AutoWave, 0, <firmware>, <outputs>, <inputs>
```

The generic `scpi-driver-core` identity parser preserves the prefix as part of the first CSV field. Do not change the generic parser for this one vendor.

AutoWave must provide vendor-specific normalization:

- strip a leading `*IDN:` from the manufacturer field for the public normalized identity;
- require model `AutoWave` case-insensitively;
- accept manufacturer `EM TEST` after normalization;
- preserve the raw response for diagnostics.

Connection API policy:

- explicit VISA resource name is the default and preferred API;
- do not search for the literal word `AutoWave` inside VISA resource names;
- optional discovery may enumerate GPIB/message-based candidates and issue the safe unframed `*IDN?` query;
- discovery must be explicitly invoked by the caller;
- discovery must use finite per-resource timeouts;
- discovery must close every rejected candidate cleanly;
- multiple matching devices must produce an ambiguity result rather than silently picking one.

## 13. GPIB response boundary

For the initial GPIB migration, response boundaries use the VISA backend-defined message boundary (EOI/END) through `ReadMode.BACKEND_DEFINED_MESSAGE`.

This applies to:

- unframed `*` command replies;
- decorated framed replies;
- one-byte ACK/NAK/NOTREADY/BUSY replies.

HIL must verify that the target VISA backend and AutoWave firmware assert/interpret END/EOI correctly for all of these response classes.

If HIL shows that one-byte replies or framed replies do not provide a reliable backend boundary, do not implement an unbounded read. Stop the migration PR and define a bounded alternative in a separately reviewed change.

## 14. Error status is destructive-on-read

The official command reference states that `STAT? ERR` is cleared after read.

Therefore:

- do not map AutoWave `STAT? ERR` onto the generic SCPI `SYST:ERR?` queue abstraction;
- do not perform automatic error reads after every command;
- expose an explicit AutoWave error/status query whose destructive read semantics are documented;
- tests must prove that no hidden post-command operation consumes the device error state.

## 15. Go-to-local semantics

The AutoWave command `*GTL` is documented to:

- stop a running test; and
- return the instrument to local mode.

This is **not equivalent** to merely deasserting VISA REN.

Therefore:

- the public AutoWave `go_to_local()`/legacy `disconnect()` behavior must use the vendor `*GTL` command;
- do not substitute `VisaTransport.go_to_local()`;
- bus-level VISA local control may be exposed separately only if a real use case requires it;
- because `*GTL` can stop an active test, it is a side-effecting operation and is never transport-replayed automatically.

## 16. File-transfer semantics

The manual explicitly states that file commands provide information/control around files but do not transfer the file payload over the command channel.

The first migration therefore supports:

- directory/path queries;
- file existence/size/detail queries;
- transfer initialization commands where already supported;
- file selection for test execution.

Actual file-content transfer is out of scope for the GPIB command driver and is performed by FTP, USB, or AutoWave control software. A future FTP helper must be a separate feature and must not be disguised as SCPI/GPIB binary transfer.

## 17. Resolved legacy discrepancies

The migration must explicitly fix the following instead of preserving them accidentally.

| Legacy behavior | Verified disposition |
| --- | --- |
| `run_test_file()` sends `STAR` twice | Bug. Official start example sends one `STAR`. New workflow sends once. |
| Break command stored as `BREAK` | Bug. Official command syntax is `BREA`. New driver uses `BREA`; compatibility impact must be documented. |
| status result labels IN1 twice | Bug. Channels are IN1 and IN2. |
| `get_dir_upgrade` assigned to UPGD then overwritten by LOGD | Bug. Expose upgrade and log directories separately. |
| `get_test_time()` comment claims protocol does not work | Stale/unverified comment. Non-`*` commands use framed protocol after protocol enable. HIL will verify CKLF specifically. |
| silent range clamping | Do not preserve. Raise typed validation errors. |
| broad retry of every exception | Do not preserve. Use explicit safe retry/BUSY rules. |
| retry exhaustion can fall through to `None` | Do not preserve. Raise a typed terminal error. |
| exception path can reference an unassigned reply variable | Do not preserve. Regression-test the failure path. |
| `*GTL` treated as ordinary disconnect text | Preserve vendor command semantics explicitly; document that it stops a running test. |

## 18. Manual inconsistencies resolved for implementation

### 18.1 VSET versus VOFS

The command reference defines:

- `VSET` = set output voltage;
- `VOFS` = set output offset.

A later initialization example labels these two rows in the opposite order. The legacy driver agrees with the command-reference definition.

Implementation uses:

```text
VSET -> voltage
VOFS -> offset
```

### 18.2 Protocol-enable syntax

The command definition gives `*PRCL:<ON/OFF>`; the initialization example is formatted as `*PRCL ON`. The legacy driver uses the colon form.

Canonical implementation:

```text
*PRCL:ON
*PRCL:OFF
```

HIL must capture the exact accepted/replied bytes.

### 18.3 Generator mode syntax

The manual's example uses `MOD GEN`, and the existing working driver generates `MOD GEN`. Preserve `MOD GEN` in the first migration. Do not "normalize" it to a colon form without HIL evidence.

### 18.4 Checksum 0x20 edge

Use the dedicated checksum section and legacy rule: a post-mask checksum of 0x20 is adjusted to 0x40. Add a specific regression/HIL vector for this boundary.

## 19. Close and shutdown semantics

Ordinary `close()`:

- closes the transport deterministically;
- does not issue `STOP`, `*GTL`, `*PRCL:OFF`, reset, or reboot implicitly.

Reason: those commands alter physical/device state and close must remain predictable even when the session is already faulted.

Provide explicit high-level methods for stop/go-local/protocol changes as needed.

Context-manager exit follows ordinary close semantics unless a future separately reviewed safety policy explicitly requires otherwise.

## 20. PR00 acceptance update

PR00 no longer needs to discover the basic protocol rules listed above. It must verify and freeze them into characterization evidence.

PR00 must produce:

- compatibility inventory;
- command inventory;
- manual-to-legacy discrepancy table;
- checksum vectors including the 0x20 edge;
- initialization/bootstrapping characterization;
- side-effect/retry classification table;
- test vectors for ACK/NAK/NOTREADY/BUSY/decorated responses;
- exact expected command bytes for representative operations;
- explicit HIL TODOs for EOI, checksum 0x20, syntax ambiguities, firmware compatibility, and CKLF framing;
- regression tests that expose known legacy defects without prematurely rewriting runtime behavior.

After PR00 is reviewed and merged, PR01 may start without unresolved P1 architectural/protocol blockers from the pre-coding review.
