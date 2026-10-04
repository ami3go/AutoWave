# AutoWave

GPIB control driver for the AutoWave EM test generator.

## Migration

The planned migration to [`scpi-driver-core`](https://github.com/ami3go/scpi-driver-core) is defined in [`docs/SCPI_DRIVER_CORE_MIGRATION_PLAN.md`](docs/SCPI_DRIVER_CORE_MIGRATION_PLAN.md). The verified protocol and recovery decisions that gate implementation are in [`docs/AUTOWAVE_PROTOCOL_BASELINE.md`](docs/AUTOWAVE_PROTOCOL_BASELINE.md).

Current repository version: **0.0.3**.

## Characterization

The pre-migration behavior and known legacy defects are frozen in [`docs/characterization/PR00_BASELINE.md`](docs/characterization/PR00_BASELINE.md). Command/replay policy is in [`docs/characterization/COMMAND_INVENTORY.md`](docs/characterization/COMMAND_INVENTORY.md), and real-instrument evidence still required is tracked in [`docs/characterization/HIL_TODO.md`](docs/characterization/HIL_TODO.md).
