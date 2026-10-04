# PR00 HIL verification backlog

These items are intentionally not claimed by hardware-free characterization. They must be
verified against a real AutoWave and the actual VISA/GPIB stack before the corresponding
production behavior is considered qualified.

## Required before HIL-qualified migration

| ID | Verification | Why simulation is insufficient | Acceptance evidence |
| --- | --- | --- | --- |
| HIL-001 | GPIB END/EOI boundary for ordinary `*IDN?` reply | depends on instrument/VISA bus behavior | one bounded read returns exactly one complete reply |
| HIL-002 | END/EOI boundary for decorated framed reply | vendor framing plus GPIB behavior | decorated reply arrives as one bounded message and checksum validates |
| HIL-003 | END/EOI boundary for one-byte ACK/NAK/NOTREADY/BUSY | some backends handle short messages differently | each byte is returned as a complete message without consuming later traffic |
| HIL-004 | raw checksum boundary where masked sum is exactly `0x20` | manual wording is internally inconsistent | target accepts adjusted checksum `0x40` |
| HIL-005 | protocol enable exact syntax | command table uses `*PRCL:<ON/OFF>`, example shows spacing | `*PRCL:ON` is accepted and protocol becomes active |
| HIL-006 | generator mode exact syntax | command table/example formatting differs | `MOD GEN` is accepted under framed protocol |
| HIL-007 | `CKLF?` behavior under framed protocol | stale legacy comment claims protocol incompatibility | framed query returns valid decorated response |
| HIL-008 | BUSY resend semantics | physical processing state is required | same encoded request after BUSY eventually completes without duplicated action |
| HIL-009 | NOTREADY behavior and flush recovery | manual describes device-side command flushing | no unrelated command is sent until the instrument is ready; recovery remains bounded |
| HIL-010 | real response latency | simulator cannot establish device processing time | normal replies observed and recorded; 2 s timeout remains comfortably bounded |
| HIL-011 | `*GTL` side effect | it can stop a running test | active test stops and local mode is restored exactly as documented |
| HIL-012 | reboot framing after protocol enable | legacy sends REB unframed | framed `REB` is accepted when protocol is active |
| HIL-013 | VSET/VOFS response type | legacy never consumes the response | reply is captured and classified as ACK/decorated as applicable |
| HIL-014 | firmware compatibility below 8.03.02 | manual claims commands require >=8.03.02 but examples use lower versions | record actual firmware and supported command subset; do not assume |
| HIL-015 | repeated open/bootstrap/close cycles | lifecycle issues can be backend-specific | no stale response, leaked session, or failed subsequent open |
| HIL-016 | recovery after an induced transport fault | requires real transport state and instrument protocol state | reopen + IDN + ECHO + PRCL restores communication without restoring physical test state |

## Bench-safety constraints

HIL that changes outputs or starts tests must use a reviewed safe bench configuration. Tests
must not assume that replaying a command is safe. In particular, a forced communications
timeout after `STAR`, `STOP`, `BREA`, VSET, VOFS, trigger, mode, reset, reboot, or file
selection must be treated as an uncertain physical outcome.

BUSY is the only protocol-defined exception: a verified BUSY reply permits bounded resend of
the exact same encoded request.

## Evidence record

For each HIL run capture:

- AutoWave model;
- firmware;
- installed modules/output/input count;
- VISA implementation/vendor and version;
- GPIB adapter/controller and driver;
- operating system;
- Python version;
- AutoWave package version/commit;
- scpi-driver-core version/commit;
- timestamp;
- exact test IDs;
- pass/fail;
- observed raw TX/RX where safe to record;
- deviations from the protocol baseline.

Any HIL result that contradicts `AUTOWAVE_PROTOCOL_BASELINE.md` blocks the affected migration
PR until the baseline is updated in a separately reviewed/versioned change.
