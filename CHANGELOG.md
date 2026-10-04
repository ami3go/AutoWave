# Changelog

All notable project changes are recorded here.

## 0.3.0 - 2026-10-04

### Added

- `AutoWaveConnection` layer on top of `ScpiSession`, `ScpiClient`, and byte transports.
- Exact unframed bootstrap sequence: `*IDN?`, `*ECHO:ON`, `*PRCL:ON`.
- Vendor-specific normalized identity model preserving the raw identification response.
- Explicit GPIB `VisaTransport` factory with bounded backend-defined-message reads.
- Bounded vendor BUSY exact-message re-query policy.
- Explicit safe-query transport recovery that reopens the core session and re-runs AutoWave bootstrap only.
- Typed connection-state, identity, and discovery errors.
- Opt-in bounded VISA discovery that never silently selects among multiple AutoWave units.
- MockTransport tests for exact byte traffic, pacing, replay policy, fault invalidation, BUSY, and recovery.
- Injected ResourceManager discovery tests and PyVISA-sim integration coverage.
- Connection/session architecture documentation.

### Changed

- Cached protocol-ready and identity state are cleared immediately after uncertain transport failures.
- Communication recovery does not restore generator mode, voltage, offset, trigger, file selection, or test execution state.
- Ordinary close remains transport-only and never sends STOP, BREA, GTL, reset, reboot, or protocol-disable commands.

## 0.2.0 - 2026-10-04

### Added

- Pure byte-oriented AutoWave STX/ETX/checksum codec with defensive command/response bounds.
- Explicit ACK, NAK, NOTREADY, BUSY, and decorated-data reply classification.
- Typed AutoWave error hierarchy integrated with `scpi-driver-core` exception categories.
- ASCII string-command encoder that refuses to frame `*` control-plane commands and refuses to guess the undocumented vendor code page.
- Byte-preserving decorated-response parser and explicit text-decoding helper.
- Deterministic Hypothesis profiles and property tests for framing round trips, corruption, truncation, control bytes, limits, and checksum invariants.
- 90% branch-coverage gate for migrated `autowave` package code.

### Changed

- Public `autowave` namespace now exports the typed AutoWave exception hierarchy.
- Protocol status parsing is separate from transport retry policy; BUSY is only classified here and is not automatically resent by the codec.

## 0.1.0 - 2026-10-04

### Added

- Modern `pyproject.toml` packaging for the `autowave-driver` distribution.
- New typed `autowave` package namespace with an explicit package version.
- Exact runtime dependency pin to the reviewed `scpi-driver-core` commit `d850f88a78ddfbfa08b667c0be6cbb0bb4a01541`.
- Packaging smoke tests for distribution metadata, the core dependency, and legacy import compatibility.
- Packaging/development documentation.
- CI gates for Python 3.10-3.13 hardware-free tests, Ruff, formatting, mypy, wheel/sdist builds, and clean artifact installation.

### Changed

- Legacy `AutoWave_class` and `Timer_class` remain installable as top-level compatibility modules without runtime refactoring.
- Development dependencies are centralized in the `dev` project extra.
- Pytest configuration is centralized in `pyproject.toml` with per-test and session timeout protection.
- Python build/cache/IDE ignore rules are normalized.

## 0.0.3 - 2026-10-04

### Added

- PR00 executable characterization suite for the legacy checksum, frame construction, command tree, retry/error behavior, initialization, and high-level workflows.
- Compatibility/public-surface baseline and explicit legacy-defect inventory.
- Command-by-command side-effect and replay classification.
- HIL verification backlog separating software evidence from physical GPIB/VISA evidence.
- Hardware-free characterization CI on Python 3.10 through 3.13.

### Changed

- Added explicit dispositions for additional legacy protocol defects found during characterization: malformed echo/protocol query strings, unframed REB after protocol enable, framed `*GTL`, write-without-read VSET/VOFS operations, and the contradictory VOFS negative-value clamp.
- PR00 remains behavior-preserving: no production runtime source has been modified.

## 0.0.2 - 2026-10-04

### Changed

- Reviewed the scpi-driver-core migration plan before runtime implementation.
- Added a verified AutoWave protocol baseline derived from the EM Test Remote Manual V6.02.02.
- Resolved pre-coding findings covering protocol bootstrap, timing, recovery, BUSY/NAK/NOTREADY behavior, GPIB message boundaries, discovery, identity normalization, local-control semantics, file-transfer scope, and defensive message bounds.
- Defined explicit dispositions for known legacy discrepancies including duplicate `STAR`, `BREAK` versus `BREA`, duplicated IN1 labels, overwritten UPGD/LOGD command storage, unsafe blanket retries, silent range clamping, and retry fall-through.
- Added mandatory HIL checks for EOI/END behavior, checksum 0x20 boundary behavior, protocol/mode syntax, firmware compatibility, and CKLF framing.
- Updated the migration plan to document the vendor-defined BUSY resend exception separately from generic transport retry.

## 0.0.1 - 2026-10-04

### Added

- Initial scpi-driver-core migration execution plan.
- Initial explicit repository version baseline.
