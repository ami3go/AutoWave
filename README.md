# AutoWave

Python driver for the EM Test AutoWave generator.

> Migration status: the repository is being migrated to the shared
> [`scpi-driver-core`](https://github.com/ami3go/scpi-driver-core) transport/session
> infrastructure. Version 0.1.0 establishes the installable package and quality gates; the
> production protocol implementation is migrated in subsequent reviewed phases.

Current repository version: **0.1.0**.

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
