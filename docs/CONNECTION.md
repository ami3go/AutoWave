# AutoWave connection and session layer

Version 0.3.0 introduces the communication layer that binds the verified AutoWave protocol to
`scpi-driver-core`. High-level instrument workflows are intentionally still outside this layer.

## Architecture

```text
future AutoWave driver methods
          |
AutoWaveConnection
          |
ScpiSession / ScpiClient
          |
Transport
          |
VisaTransport -> PyVISA -> GPIB
```

The production constructor for the current migration target is:

```python
from autowave import AutoWaveConnection

with AutoWaveConnection.visa("GPIB0::5::INSTR") as connection:
    print(connection.identity)
```

Only explicit GPIB `::INSTR` resources are accepted by this constructor in v0.3.0. TCP,
serial, USB, and other transport profiles are not silently treated as equivalent.

## Communication defaults

- operation timeout: 2.0 s;
- minimum inter-command interval: 0.250 s;
- command payload bound: 4096 bytes;
- response message bound: 65536 bytes;
- GPIB response boundary: VISA backend-defined message/EOI;
- ordinary close: transport cleanup only, with no STOP, GTL, reset, or reboot.

## Bootstrap

A successful `open()` performs exactly:

```text
*IDN?
*ECHO:ON
*PRCL:ON
```

All three are unframed control-plane transactions. The identity is normalized and validated as
EM TEST / AutoWave before protocol readiness is reported.

Generator mode, selected files, trigger settings, outputs, offsets, and running tests are not
part of communication bootstrap.

## Identity

`parse_autowave_identity()` accepts the vendor-prefixed form:

```text
*IDN:EM TEST, AutoWave, 0, 8.03.02, 4, 2
```

and the equivalent form without the `*IDN:` prefix. It preserves:

- manufacturer;
- model;
- serial;
- firmware;
- output count when present;
- input count when present;
- exact raw response.

A response from another manufacturer/model is an `AutoWaveIdentityError`.

## Framed transactions

`transact_framed()`:

1. requires a successful communication bootstrap;
2. creates one exact frame with `autowave.protocol`;
3. performs one bounded backend-message transaction;
4. parses the complete reply;
5. handles BUSY only under the vendor-specific bounded policy;
6. returns ACK or DATA;
7. raises typed NAK/NOTREADY/protocol errors.

The default transport replay policy is `ReplayPolicy.NEVER`.

## BUSY policy

A verified BUSY byte is not a transport error. It authorizes sending the exact same already
encoded frame again.

Default bounds:

```text
maximum sends: 10
maximum BUSY-requery elapsed time: 5.0 s
```

The elapsed budget starts when BUSY is first observed. The normal 250 ms pacing still applies
between sends. Reaching either bound raises `AutoWaveBusyError`.

NAK, NOTREADY, malformed replies, checksum errors, and transport timeouts never enter this
BUSY loop.

## Safe transport retry

Generic retry is rejected unless the caller explicitly supplies:

```python
replay_policy=ReplayPolicy.SAFE
```

and a core `RetryPolicy`.

On a retryable transport failure:

1. the transport must be FAULTED;
2. the core session reopens it;
3. AutoWave re-runs only `*IDN?`, `*ECHO:ON`, and `*PRCL:ON`;
4. the safe operation may then be replayed.

Physical/application state is never restored automatically.

A timeout without explicit safe replay leaves protocol readiness and cached identity invalidated.

## Control-plane transactions

`control_transaction()` is for commands beginning with `*`. It does not frame them.
Retry is subject to the same explicit `ReplayPolicy.SAFE` rule.

This low-level method does not decide that `*GTL`, reset, or any other control command is safe.
That semantic classification belongs to concrete driver methods.

## Discovery

Explicit resource names remain preferred.

Optional discovery requires an application-owned/borrowed VISA ResourceManager:

```python
from autowave import discover_autowave_resources

matches = discover_autowave_resources(resource_manager)
```

Discovery:

- scans only GPIB `::INSTR` candidates by default;
- sends only bounded, unframed `*IDN?`;
- closes every candidate resource;
- skips unreachable/non-AutoWave candidates;
- returns all matches;
- never silently chooses among multiple instruments.

`require_single_autowave()` converts zero or multiple matches into a typed discovery error.

The discovery helper never closes the supplied ResourceManager; ownership remains with the
application/PyVISA lifecycle.

## Tests

PR03 validates the layer through:

- core `MockTransport` exact-byte tests;
- transport-fault and safe-recovery tests;
- bounded BUSY tests;
- pacing tests with an injected monotonic clock;
- discovery with an injected fake VISA manager;
- the real `VisaTransport -> PyVISA -> PyVISA-sim` stack;
- Python 3.10-3.13 CI;
- strict typing and branch coverage.

Real END/EOI and vendor VISA/GPIB behavior remain HIL evidence.
