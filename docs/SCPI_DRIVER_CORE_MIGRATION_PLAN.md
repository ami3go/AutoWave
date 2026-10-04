# AutoWave migration plan to scpi-driver-core

**Document version:** 1.1  
**Current planning version:** `0.3.0`  
**Repository baseline:** `ami3go/AutoWave` main  
**Initial repository version introduced with this plan:** `0.0.1`  
**Target shared core:** `ami3go/scpi-driver-core`  
**Core baseline observed when this plan was written:** `0.1.0.dev6` at `d850f88a78ddfbfa08b667c0be6cbb0bb4a01541`

## 1. Purpose

This document is the implementation contract for migrating the AutoWave Python driver from its current direct-PyVISA design to `scpi-driver-core`.

The migration must improve reliability, testability, packaging, diagnostics, and maintainability without changing valid AutoWave instrument behavior. It must preserve AutoWave-specific protocol semantics, especially the proprietary framed protocol:

```text
STX 0x02 + command bytes + ETX 0x03 + checksum
```

and the device-specific single-byte responses such as BUSY, NOT READY, and NAK.

The code agent executing this plan must work incrementally. Each feature or migration slice must be implemented, tested, reviewed, corrected, submitted through a pull request, and merged before dependent work proceeds.

The migration is not considered complete merely because tests pass. Completion requires a final independent deep review, disposition of every finding, fixes for blocking findings, a full regression rerun, and hardware-in-the-loop evidence for behavior that simulation cannot establish.

### 1.1 Resolved pre-coding findings

The mandatory verified protocol/transport decisions are defined in [`AUTOWAVE_PROTOCOL_BASELINE.md`](AUTOWAVE_PROTOCOL_BASELINE.md). That document is part of this implementation contract.

The pre-coding review findings are resolved as follows:

- official source of truth: EM Test AutoWave Remote Manual V6.02.02, with explicit evidence precedence;
- protocol bootstrap: power-up protocol OFF; `*` commands always unframed; bootstrap is `*IDN?` -> `*ECHO:ON` -> `*PRCL:ON`;
- recovery: transport/session recovery must be followed by AutoWave bootstrap, but must not restore generator/output/test state;
- timing: minimum 250 ms between commands; no artificial delay between write and read within one transaction; initial bounded timeout remains 2.0 s;
- response boundary: GPIB uses bounded VISA backend-defined message/EOI semantics, with HIL verification required;
- discovery: explicit VISA resource is preferred; optional discovery uses bounded unframed `*IDN?` and identity matching rather than resource-name substring matching;
- health/identity: `*IDN?` remains valid after protocol enable because `*` commands are never framed; AutoWave-specific normalization handles the vendor `*IDN:` prefix;
- BUSY: verified `0x19` permits bounded resend of the exact same message as vendor-defined polling; this is not generic transport retry;
- NOTREADY/NAK/timeout: never trigger automatic replay of a side-effecting operation;
- local control: public AutoWave local control uses vendor `*GTL`, which can stop a running test; VISA REN control is not a substitute;
- destructive error status: `STAT? ERR` clears on read and must not be wired to automatic generic SCPI error-queue checking;
- defensive bounds: 4096-byte command payload and 65536-byte response/message limits for the initial migration;
- file payload transfer: actual file content is not transferred over GPIB command traffic; FTP/USB/control software is separate;
- known legacy discrepancies, including duplicate `STAR`, `BREAK` versus documented `BREA`, duplicated IN1 labels, and overwritten LOGD/UPGD command storage, have explicit dispositions in the protocol baseline.

No runtime migration phase may reopen these decisions casually. If HIL contradicts the baseline, stop the affected PR, record the evidence, update the baseline in a separately reviewed/versioned change, then continue.

## 2. Mandatory design boundaries

The final dependency direction must be:

```text
AutoWave public driver API
        |
AutoWave device semantics
        |
AutoWave protocol framing/parsing
        |
ScpiSession / ScpiClient
        |
Transport
        |
VisaTransport -> PyVISA -> GPIB/VISA backend
```

### 2.1 What belongs in AutoWave

The AutoWave repository owns:

- AutoWave command names and command trees.
- STX/ETX/checksum framing.
- BUSY, NOT READY, NAK, and other vendor-specific reply interpretation.
- AutoWave file/test execution workflows.
- channel semantics;
- voltage and offset limits;
- generator modes;
- status-code interpretation;
- safe instrument initialization and shutdown policy;
- compatibility behavior for the legacy public API;
- AutoWave-specific HIL tests and simulator fixtures.

### 2.2 What belongs in scpi-driver-core

Reuse the core for:

- VISA transport ownership and lifecycle;
- bounded byte reads/writes;
- transport state and invalidation;
- session health and reconnect behavior;
- command serialization;
- pacing;
- safe retry infrastructure;
- operation identifiers;
- tracing/audit support;
- common typed transport/protocol exceptions;
- deterministic scripted/mock testing;
- PyVISA integration patterns.

Do not copy these mechanisms into AutoWave.

### 2.3 When scpi-driver-core may be changed

Do not modify `scpi-driver-core` merely to reduce AutoWave boilerplate.

If the migration exposes a missing primitive:

1. prove that the requirement is generic rather than AutoWave-specific;
2. document at least one additional credible driver use case;
3. create a separate `scpi-driver-core` issue/PR;
4. add core tests first;
5. complete core review and CI;
6. increment the core version;
7. merge the core PR;
8. pin/update AutoWave to the new core version in a separate AutoWave PR;
9. only then continue the dependent AutoWave feature.

AutoWave-specific STX/ETX/checksum behavior must remain in AutoWave unless multiple real drivers demonstrate the same protocol abstraction.

## 3. Safety and behavioral rules

The code agent must treat all commands as potentially side-effecting unless proven otherwise.

Never automatically replay operations such as:

- `STAR`
- `STOP`
- `BREA`
- `TRIG:GEN ...`
- output or voltage-setting commands;
- file-selection or file-transfer commands;
- reset/reboot commands;
- mode changes;
- commands whose completion state is uncertain after a timeout.

Queries may use retry only after they are explicitly classified as safe to replay.

The only protocol-level resend exception is a verified one-byte BUSY (`0x19`) reply. The official protocol requires resending the exact previous message to obtain completion. This BUSY loop is bounded, paced, and separate from generic transport retry. NAK, NOTREADY, timeout, malformed response, or checksum failure must not enter the BUSY resend path.

An uncertain timeout must never allow a late reply to be consumed as the response to a subsequent command. Reuse the core invalidation/recovery semantics rather than trying to drain or guess around an unknown stream state.

Do not silently clamp invalid requested values. Public setters must validate input and raise a typed exception unless the existing hardware/manual explicitly defines saturation as the intended behavior.

All production waits, polls, reads, retries, and recovery loops must be bounded.

## 4. Compatibility strategy

The migration should preserve existing useful public behavior where practical, but compatibility must not preserve known unsafe defects.

Before implementation, create a compatibility inventory containing:

- public classes;
- public methods;
- method signatures;
- default arguments;
- return values;
- exceptions;
- command strings generated;
- initialization sequence;
- timing requirements;
- any scripts/examples that import the current module.

Classify each item as:

- **preserve** — same public behavior;
- **preserve with deprecation** — retained temporarily with warning;
- **intentional breaking fix** — unsafe/incorrect behavior changed deliberately;
- **remove** — obsolete and explicitly documented.

Every intentional breaking change must appear in the changelog and migration guide.

## 5. Versioning rules

The repository starts explicit version tracking with `0.0.1`.

Every merged implementation PR must increment the repository version. Do not merge several independently reviewable features under one silent version.

Recommended pre-1.0 progression:

```text
0.0.1  migration plan / version baseline
0.0.2  pre-coding review findings resolved / verified protocol baseline
0.0.3  PR00 baseline characterization and compatibility inventory
0.1.0  packaging and public package skeleton
0.2.0  AutoWave protocol codec and typed errors
0.3.0  scpi-driver-core VISA/session integration
0.4.0  migrated command API and compatibility layer
0.5.0  high-level AutoWave workflows
0.6.0  complete hardware-free validation and CI
0.7.0  HIL-qualified migration candidate
0.8.0  final-review findings resolved
1.0.0  production migration accepted
```

Patch releases may be used for review fixes within a phase. The exact sequence may change, but every repository change must have an explicit version increment and changelog entry after packaging/changelog infrastructure exists.

During migration, never depend on a floating `scpi-driver-core` `main`. Record and pin either an exact released version or an exact commit SHA. Update that pin only in a reviewed dependency-update PR.

## 6. Branch and pull-request policy

Use short-lived branches. Do not perform the entire migration in one branch.

Recommended naming:

```text
migration/00-baseline
migration/01-packaging
migration/02-protocol
migration/03-core-transport
migration/04-driver-api
migration/05-workflows
migration/06-validation
migration/07-hil
migration/08-final-review-fixes
```

Each PR must:

- have one primary migration purpose;
- increment the version;
- update the changelog once introduced;
- include tests for the changed behavior;
- include the agent's self-review;
- include a separate review pass after implementation;
- list all findings and their disposition;
- have green required CI before merge;
- contain no unrelated refactoring;
- be mergeable independently;
- leave `main` in a usable state.

Do not start a dependent PR before the prior required PR is merged unless an explicit stacked-PR strategy is documented.

## 7. Per-feature implementation and review loop

The following loop is mandatory for every feature, not only for every phase.

### Step A — define the feature contract

Before editing code, write down:

- public behavior being added or migrated;
- exact commands/replies involved;
- transport assumptions;
- side effects;
- retry classification;
- timeout behavior;
- failure modes;
- compatibility impact;
- tests required;
- HIL requirement, if any.

### Step B — implement the smallest complete vertical slice

A vertical slice should contain device logic plus its tests. Avoid large speculative abstractions.

### Step C — run focused validation

Run the smallest relevant tests first, then the complete hardware-free suite.

At minimum after test infrastructure exists:

```bash
ruff check .
ruff format --check .
mypy src
pytest -m "not hardware"
python -m build
```

Use coverage reporting and preserve the configured coverage gate.

### Step D — mandatory post-feature review

After the feature works, stop implementation and review the changed code as if reviewing another developer's PR.

Review specifically for:

- wrong AutoWave command syntax;
- incorrect STX/ETX/checksum behavior;
- unsafe command replay;
- unbounded waits or reads;
- stale-response hazards;
- incorrect transport recovery;
- hidden broad `except Exception`;
- swallowed failures;
- accidental `None` returns after retry exhaustion;
- use of `print` instead of structured diagnostics;
- silent range clamping;
- locking/deadlock risks;
- resource leaks;
- public API regressions;
- missing tests;
- tests that mock away the actual core integration;
- vendor-specific code leaking into `scpi-driver-core`;
- undocumented breaking changes.

### Step E — record review findings

Classify every finding:

- **P0 Critical** — can cause unsafe physical behavior, corruption, wrong command execution, or unrecoverable protocol desynchronization.
- **P1 High** — reliability/API defect, hang risk, incorrect retry/recovery, resource leak, or major compatibility regression.
- **P2 Medium** — maintainability/test/documentation weakness that should normally be fixed before phase completion.
- **P3 Low** — cleanup or optional improvement.

For the feature PR:

- P0: must be fixed before PR review can continue.
- P1: must be fixed before merge.
- P2: fix before merge unless a documented follow-up issue is justified.
- P3: may be deferred with an issue/reference.

### Step F — fix and re-run

After each fix, rerun the tests relevant to the finding. Before merge, rerun the whole hardware-free gate.

### Step G — open PR and perform PR-level review

The PR description must contain:

- feature contract;
- architecture impact;
- compatibility impact;
- retry/safety classification;
- tests run;
- review findings;
- fixes applied;
- remaining accepted limitations;
- HIL evidence or HIL TODO.

### Step H — merge gate

Merge only when:

- required CI is green;
- no P0/P1 findings remain;
- required P2 findings are resolved or explicitly tracked;
- version/changelog are correct;
- documentation matches behavior;
- no dependency on an unmerged core change remains.

## 8. Migration PR sequence

### PR 00 — baseline characterization and migration scaffolding

**Goal:** establish a reproducible behavioral baseline before refactoring.

Tasks:

- inventory current repository structure;
- build the compatibility and command inventories against `AUTOWAVE_PROTOCOL_BASELINE.md`;
- freeze the verified STX/ETX/checksum rules into characterization vectors;
- add vectors for ACK, NAK, NOTREADY, BUSY, and decorated responses;
- characterize the legacy initialization sequence against the verified bootstrap sequence;
- characterize the legacy timing/retry behavior without preserving unsafe retry semantics;
- identify every command with physical side effects and assign its replay policy;
- create the manual-to-legacy discrepancy table;
- document existing defects separately from intended compatibility;
- record explicit HIL TODOs for EOI/END behavior, checksum 0x20 edge behavior, firmware compatibility, `*PRCL:ON`, `MOD GEN`, and CKLF framing;
- introduce package/test tooling needed for the next PR if it can be done without moving runtime behavior.

Required tests:

- characterization tests for checksum, including manual vectors and the 0x20 boundary;
- characterization tests for command construction and exact bytes;
- characterization vectors for all four simple one-byte protocol replies;
- regression tests for deterministic legacy defects that will later be fixed.

Review gate:

- confirm characterization describes the current driver separately from the desired target behavior;
- confirm all deviations from the verified protocol baseline are recorded;
- confirm no runtime behavior was accidentally changed;
- confirm no unresolved P1 protocol/architecture question remains before PR01.

Merge before PR 01.

**PR00 deliverables:** [legacy baseline](characterization/PR00_BASELINE.md), [command/replay inventory](characterization/COMMAND_INVENTORY.md), and [HIL backlog](characterization/HIL_TODO.md).

### PR 01 — modern Python package and project structure

**Goal:** make AutoWave installable and testable without changing instrument semantics.

Target layout:

```text
src/
  autowave/
    __init__.py
    driver.py
    protocol.py
    commands.py
    errors.py
    models.py
tests/
  unit/
  integration/
  property/
  hardware/
examples/
docs/
```

Tasks:

- add `pyproject.toml`;
- define supported Python versions compatible with the selected core;
- make `scpi-driver-core` an explicit dependency;
- add dev/test dependencies;
- add `py.typed` if the package is typed;
- add changelog;
- add CI;
- add pytest markers including `hardware`;
- add pytest-timeout bounds;
- make wheel and sdist build successfully;
- preserve a compatibility import path if required.

Do not rewrite the protocol in this PR.

Review gate:

- install wheel into a clean environment;
- import package;
- run hardware-free CI;
- inspect runtime dependencies to ensure test tools are not runtime requirements.

Merge before PR 02.

**PR01 deliverables:** installable `autowave-driver` distribution, typed `autowave` namespace,
legacy top-level compatibility modules, exact `scpi-driver-core` commit pin, package smoke
tests, and CI that validates the hardware-free matrix plus clean wheel/sdist installation.

### PR 02 — AutoWave protocol codec and typed errors

**Goal:** isolate proprietary framing from transport and business logic.

Implement explicit functions/classes for:

- command text -> bytes;
- checksum calculation;
- frame encoding;
- response frame decoding;
- STX validation;
- ETX validation;
- checksum validation;
- text decoding;
- special one-byte response handling.

Introduce typed errors such as:

```text
AutoWaveError
AutoWaveProtocolError
AutoWaveChecksumError
AutoWaveBusyError
AutoWaveNotReadyError
AutoWaveNakError
AutoWaveResponseError
AutoWaveValidationError
```

Do not perform VISA I/O inside the protocol codec.

Required tests:

- known checksum vectors from the legacy implementation/manual;
- empty/minimal payload edge cases;
- non-ASCII rejection unless manual proves another encoding;
- malformed STX;
- malformed ETX;
- bad checksum;
- truncated frame;
- oversized frame;
- ACK;
- BUSY;
- NOT READY;
- NAK;
- valid reply round trip;
- Hypothesis properties for encode/decode/checksum invariants and corrupt/truncated inputs.

Review gate:

- byte-for-byte comparison against known legacy traffic;
- no transport imports in protocol module;
- no generic-core modification unless separately approved.

Merge before PR 03.

**PR02 deliverables:** pure byte-oriented framing/checksum/reply parser, typed AutoWave errors,
manual checksum vectors, deterministic unit/property coverage, explicit status classification,
and no transport/session imports in the protocol layer.

### PR 03 — scpi-driver-core transport/session integration

**Goal:** replace direct ResourceManager/resource ownership with core infrastructure.

Implement:

- `VisaTransport`;
- `ScpiClient`;
- `ScpiSession`;
- unframed control-plane codec with no CR/LF terminator for GPIB message-based traffic;
- bounded GPIB `BACKEND_DEFINED_MESSAGE` response requests;
- 4096-byte command and 65536-byte response/message bounds;
- minimum command interval of 0.250 s using core pacing;
- initial bounded operation timeout of 2.0 s;
- context-manager cleanup;
- explicit connection/open/close state;
- instrument identity validation;
- deterministic recovery policy;
- AutoWave recovery callback that performs core recovery followed by `*IDN?`, `*ECHO:ON`, and `*PRCL:ON`;
- explicit resource-address connection API plus optional bounded identity-based discovery.

The AutoWave framed transaction should use byte operations such as `write_bytes`, `read_bytes`, or `transact_bytes` as appropriate. Do not force proprietary frames through ordinary newline-based SCPI text framing.

A verified BUSY reply may trigger a bounded resend of the identical frame according to the protocol baseline. Transport timeout, NAK, NOTREADY, checksum error, and malformed response must never be converted into that resend path.

For safe-query retry after a fault, the retry recovery callback must restore both transport state and AutoWave protocol bootstrap. Bare `ScpiSession.recover_if_faulted` is insufficient for framed commands.

Remove direct runtime ownership of `pyvisa.ResourceManager()` from the driver.

Required tests:

- successful connect and identity;
- close is idempotent;
- failed connect;
- timeout faults/invalidation behavior;
- no late response reuse;
- pacing behavior with an injected clock;
- independent sessions do not invalidate one another;
- PyVISA-sim coverage where representable;
- scripted transport coverage for proprietary frames.

Review gate:

- verify no ResourceManager lifetime regression;
- verify finite bounds;
- verify correct VISA message-boundary assumptions;
- verify no automatic replay of writes;
- verify reconnect only happens under explicit approved policy.

Merge before PR 04.

**PR03 deliverables:** `AutoWaveConnection` over `ScpiSession`/`ScpiClient`, explicit
GPIB `VisaTransport` construction, bounded backend-message reads, 250 ms pacing, verified
bootstrap, identity normalization, bounded BUSY exact-message re-query, safe-query recovery,
opt-in discovery, MockTransport coverage, and PyVISA-sim integration.

### PR 04 — command model and public driver API

**Goal:** migrate command construction and expose a clean public driver API.

Replace the legacy command-helper object tree only where doing so improves auditability. Prefer explicit methods over a generic DSL.

Migrate at least:

- identity;
- reset;
- vendor local control (`*GTL`) and its stop-test side effect;
- echo/protocol enable;
- generator mode;
- voltage;
- offset;
- status;
- trigger mode;
- file selection;
- directory/file queries.

Replace silent `range_check` clamping with typed validation unless saturation is explicitly required by the instrument specification.

Define stable public method names and type hints.

Provide a temporary compatibility facade for legacy callers if practical.

Required tests:

- exact generated commands;
- channel limits;
- voltage/offset boundaries;
- invalid channel/value errors;
- return-type parsing;
- compatibility facade behavior;
- deprecation warnings where applicable.

Review gate:

- compare public API against the compatibility inventory;
- manually inspect every side-effecting command;
- ensure no setter/query is incorrectly classified for retry.

Merge before PR 05.

### PR 05 — high-level AutoWave workflows

**Goal:** migrate operational workflows without reintroducing transport logic.

Migrate and test:

- initialization;
- run test file;
- get test duration/details;
- check test status;
- DC voltage;
- DC offset;
- disconnect/go local;
- reboot;
- stop/break behavior;
- file metadata/transfer-initialization behavior currently supported; actual file payload transfer remains out of GPIB scope.

Replace fixed sleeps with:

- core pacing when it is an inter-command minimum;
- bounded polling when waiting for a state transition;
- explicit documented settling delay only when the instrument specification requires a true dwell.

Never convert an uncertain command timeout into an automatic replay for an operation that can start/stop/trigger/change output.

Required scripted scenarios:

- normal run with exactly one `STAR` command;
- BUSY exact-message resend to completion within bounds;
- NOT READY;
- NAK;
- malformed framed reply;
- timeout before command delivery;
- timeout after delivery is uncertain;
- disconnect/reconnect;
- status sequence to completion;
- status sequence to failure;
- bounded timeout waiting for completion.

Review gate:

- trace each workflow command-by-command;
- confirm the physical side-effect model;
- confirm every loop has a deadline;
- confirm failures propagate as typed exceptions.

Merge before PR 06.

### PR 06 — complete hardware-free validation and CI hardening

**Goal:** reach production-grade software evidence without requiring hardware in normal CI.

Required layers:

1. pytest unit tests;
2. ScriptedScpiTransport/mock integration;
3. Hypothesis property tests;
4. PyVISA-sim integration where representable;
5. pytest-timeout watchdog coverage;
6. package build;
7. lint;
8. formatting check;
9. strict/static typing where configured;
10. coverage gate.

Test through the public AutoWave API whenever possible.

Add regression tests for every bug fixed during migration, including the legacy retry-handler failure where a reply variable can be referenced before assignment.

Review gate:

- deliberately inject malformed data, timeouts, and disconnects;
- inspect whether tests accidentally mock internal core behavior instead of exercising it;
- verify default CI requires no hardware.

Merge before PR 07.

### PR 07 — hardware-in-the-loop qualification

**Goal:** establish evidence simulation cannot provide.

HIL must verify at minimum:

- real GPIB/VISA explicit-resource open and optional discovery;
- correct unframed `*IDN?`/identity normalization path before and after protocol enable;
- actual STX/ETX/checksum frames;
- checksum raw-0x20 boundary behavior;
- exact `*PRCL:ON` syntax and reply;
- exact `MOD GEN` syntax and reply;
- CKLF framed-query behavior;
- command pacing on the real instrument;
- BUSY/NOT READY/NAK handling where reproducible;
- END/EOI behavior;
- timeout and recovery behavior;
- set voltage on every supported channel within a safe bench configuration;
- offset behavior;
- generator mode changes;
- test-file selection/run;
- status polling through completion;
- stop/break;
- go-to-local behavior;
- safe close/cleanup;
- repeated open/run/close cycles;
- soak test if the driver will be used in long-running automation.

All HIL tests must be marked `hardware` and excluded from normal CI unless a dedicated runner exists.

Record:

- instrument model;
- firmware;
- VISA backend/vendor;
- GPIB adapter/controller;
- Python version;
- core version/commit;
- AutoWave version;
- test date;
- pass/fail result;
- observed quirks.

Review gate:

- distinguish software evidence from physical-bus evidence;
- do not waive a failed HIL case because simulation passed.

Merge before PR 08.

### PR 08 — migration documentation and compatibility cleanup

**Goal:** prepare the migration candidate for final review.

Tasks:

- complete README;
- installation instructions;
- usage examples;
- architecture diagram;
- protocol documentation;
- compatibility/migration guide;
- troubleshooting;
- testing guide;
- HIL guide;
- dependency/version policy;
- deprecation plan;
- changelog;
- release checklist.

Review gate:

- execute documented installation in a clean environment;
- execute examples against simulator and, where applicable, hardware;
- verify every documented API exists.

Merge before final deep review.

## 9. Pull-request merge sequence

The default dependency chain is:

```text
PR00 baseline
  -> PR01 packaging
    -> PR02 protocol
      -> PR03 core transport/session
        -> PR04 public API
          -> PR05 workflows
            -> PR06 validation/CI
              -> PR07 HIL
                -> PR08 docs/cleanup
                  -> FINAL DEEP REVIEW
                    -> FIX PR(s)
                      -> FINAL VERIFICATION
                        -> production release
```

Do not squash unresolved review findings into a later unrelated PR.

If a PR uncovers a required core change:

```text
AutoWave PR pauses
   |
scpi-driver-core issue
   |
core tests + implementation PR
   |
core review/fixes
   |
core version increment + merge/release
   |
AutoWave dependency-update PR
   |
resume AutoWave feature
```

## 10. Final deep review

After PR 08, perform a new review from the current merged `main`; do not rely on the accumulated per-PR reviews.

The final reviewer should assume the migration may contain architectural mistakes even though CI is green.

Review areas:

### Architecture

- dependency direction;
- separation of device semantics/protocol/transport;
- absence of duplicate core functionality;
- absence of AutoWave semantics in the generic core.

### Protocol correctness

- frame construction;
- checksum algorithm;
- STX/ETX handling;
- special reply bytes;
- encoding;
- maximum message sizes;
- truncated/malformed response behavior.

### Transport and concurrency

- session lifecycle;
- ResourceManager handling;
- serialization;
- timeout invalidation;
- recovery;
- stale reply prevention;
- context-manager cleanup;
- deadlock potential.

### Physical safety

- command replay policy;
- trigger/start/stop semantics;
- voltage/offset validation;
- reboot/reset behavior;
- safe initialization;
- safe close;
- behavior after partial failure.

### API and compatibility

- signatures;
- defaults;
- return types;
- typed exceptions;
- deprecations;
- intentional breaking changes.

### Test quality

- coverage quality rather than only percentage;
- public-API testing;
- fault injection;
- property tests;
- simulator realism;
- watchdog tests;
- HIL evidence;
- regression tests for every discovered defect.

### Packaging and operations

- clean installation;
- build artifacts;
- dependency pins;
- supported Python versions;
- logging/tracing;
- documentation;
- version/changelog consistency.

## 11. Final findings document

Create:

```text
docs/reviews/final-migration-review.md
```

It must include:

- review date;
- reviewed AutoWave commit;
- reviewed `scpi-driver-core` version/commit;
- environment;
- reviewer scope;
- findings table;
- severity;
- affected file/API;
- technical explanation;
- safety/reliability impact;
- proposed fix;
- disposition;
- fix PR/commit;
- verification evidence.

No finding may disappear from the document. Closed findings remain listed with their resolution.

## 12. Final finding-fix loop

After the deep review:

1. freeze feature development;
2. group related findings into small fix PRs;
3. increment version for every merged fix PR;
4. add a regression test before or with every defect fix where technically possible;
5. fix all P0 and P1 findings;
6. fix P2 findings unless explicitly accepted with rationale;
7. update the final review disposition;
8. rerun the focused test for each fix;
9. rerun complete hardware-free CI;
10. rerun affected HIL tests;
11. rerun the full HIL qualification if a fix touches protocol, transport, retry, initialization, output control, trigger/start/stop, or recovery;
12. perform a final review of the fixes themselves.

The process repeats until:

- P0 open findings = 0;
- P1 open findings = 0;
- P2 open findings are either 0 or explicitly accepted and tracked;
- CI is fully green;
- required HIL is green;
- packaging/install verification passes;
- documentation matches the final implementation.

## 13. Production acceptance criteria

The migration is complete only when all of the following are true:

- AutoWave is an installable Python package;
- direct PyVISA lifecycle code is replaced by `scpi-driver-core`;
- proprietary AutoWave protocol behavior remains in AutoWave;
- all I/O and polling are bounded;
- unsafe automatic retries are eliminated;
- validation raises typed errors rather than silently altering requested values;
- deterministic cleanup is implemented;
- unit/scripted/property/PyVISA-sim/watchdog tests are present as applicable;
- normal CI requires no hardware;
- HIL validates real GPIB/VISA behavior;
- compatibility changes are documented;
- final deep review is complete;
- all P0/P1 findings are fixed;
- fix regressions are tested;
- repository version and changelog are current;
- release artifacts build and install cleanly.

Only after these criteria are met should the migration be marked production-ready and considered evidence toward the representative-driver migration requirement of `scpi-driver-core`.

## 14. Agent completion rule

A code agent must never report a phase, PR, or the overall migration as finished solely because code was generated or because one test command passed.

For every completed feature it must state:

- what changed;
- version change;
- tests executed;
- review performed;
- findings discovered;
- fixes made;
- remaining limitations;
- PR URL/number;
- merge status;
- next permitted PR in the sequence.

For the final migration it must additionally provide the final-review document, finding dispositions, CI result, HIL evidence, and production acceptance checklist.
