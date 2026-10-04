# AutoWave

Python driver for the EM Test AutoWave generator.

> Migration status: the repository is being migrated to the shared
> [`scpi-driver-core`](https://github.com/ami3go/scpi-driver-core) transport/session
> infrastructure. Version 0.4.0 adds the typed public AutoWave driver API with validated commands, strict voltage/offset/channel checks, typed status results, and explicit safe-query versus side-effect replay policy. High-level multi-command workflows remain in PR05.

Current repository version: **0.4.0**.

## Installation

For development:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The installable distribution is `autowave-driver` and the future public package namespace is:

```python
import autowave

print(autowave.__version__)
```

During the compatibility period the legacy imports remain packaged:

```python
import AutoWave_class
import Timer_class
```

See [`docs/PACKAGING.md`](docs/PACKAGING.md) for supported Python versions, clean-build
verification, dependency pinning, and development commands.

## Migration specification

The migration execution contract is
[`docs/SCPI_DRIVER_CORE_MIGRATION_PLAN.md`](docs/SCPI_DRIVER_CORE_MIGRATION_PLAN.md).
Verified protocol/recovery decisions are in
[`docs/AUTOWAVE_PROTOCOL_BASELINE.md`](docs/AUTOWAVE_PROTOCOL_BASELINE.md).

## Characterization

The pre-migration behavior and known legacy defects are frozen in
[`docs/characterization/PR00_BASELINE.md`](docs/characterization/PR00_BASELINE.md).
Command/replay policy is in
[`docs/characterization/COMMAND_INVENTORY.md`](docs/characterization/COMMAND_INVENTORY.md),
and real-instrument evidence still required is tracked in
[`docs/characterization/HIL_TODO.md`](docs/characterization/HIL_TODO.md).

## Protocol layer

The vendor STX/ETX/checksum framing and reply parser are implemented in
[`autowave.protocol`](src/autowave/protocol.py). The codec is intentionally transport-free:
it does not open VISA resources, sleep, retry, recover sessions, or execute workflows.

See [`docs/PROTOCOL.md`](docs/PROTOCOL.md) for the API and safety boundaries.

## Connection layer

The communication/session integration is implemented in
[`autowave.connection`](src/autowave/connection.py). It owns explicit GPIB/VISA connection,
AutoWave bootstrap, bounded framed transactions, vendor BUSY handling, discovery, and
safe-query recovery without restoring physical/application state.

See [`docs/CONNECTION.md`](docs/CONNECTION.md) for architecture and safety behavior.

## Public driver API

The preferred API is now exported directly from `autowave`:

```python
from autowave import AutoWave, GeneratorMode, TriggerMode

with AutoWave.visa("GPIB0::5::INSTR") as aw:
    aw.set_generator_mode(GeneratorMode.GENERATOR)
    aw.set_voltage(13.5, channel=1)
    aw.set_offset(-5.0, channel=1)
    status = aw.query_test_status()
```

See [`docs/DRIVER_API.md`](docs/DRIVER_API.md) for command semantics, validation,
status types, file/directory queries, and replay-safety rules.
