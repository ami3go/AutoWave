# Changelog

All notable project changes are recorded here.

## 0.0.3 - 2026-10-04

### Added

- PR00 executable characterization suite for the legacy checksum, frame construction, command tree, retry/error behavior, initialization, and high-level workflows.
- Compatibility/public-surface baseline and explicit legacy-defect inventory.
- Command-by-command side-effect and replay classification.
- HIL verification backlog separating software evidence from physical GPIB/VISA evidence.
- Hardware-free characterization CI on Python 3.10 through 3.13.

### Changed

- Added explicit dispositions for additional legacy protocol defects found during characterization: malformed echo/protocol query strings, unframed REB after protocol enable, framed `*GTL`, and write-without-read VSET/VOFS operations.
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
