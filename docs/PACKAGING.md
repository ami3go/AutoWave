# Packaging and development environment

AutoWave is packaged as the Python distribution `autowave-driver`.

## Import names

The migration introduces the future package namespace:

```python
import autowave
```

The existing modules remain installable during the compatibility period:

```python
import AutoWave_class
import Timer_class
```

PR01 does not redirect or rewrite the legacy implementation. Later migration phases replace
its internals behind reviewed compatibility boundaries.

## Supported Python versions

The migration baseline supports CPython 3.10 through 3.13, matching the pinned
`scpi-driver-core` baseline.

## scpi-driver-core dependency

Until the core has a production release, AutoWave pins the exact reviewed commit:

```text
scpi-driver-core 0.1.0.dev6
d850f88a78ddfbfa08b667c0be6cbb0bb4a01541
```

The dependency is represented as a PEP 508 direct Git reference in `pyproject.toml`.
Do not replace it with a floating branch. When scpi-driver-core publishes an accepted release,
use a dedicated dependency-update PR to replace the Git pin with the released version.

## Development setup

Create a virtual environment, then install the project and all development tools:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The compatibility `requirements-dev.txt` delegates to this same extra so dependency lists
do not drift.

## Quality commands

```bash
ruff check .
ruff format --check .
mypy src/autowave
pytest -m "not hardware"
python -m build
```

Normal CI must not require an AutoWave instrument.

## Build and clean-install verification

Build both distribution formats:

```bash
python -m build
```

CI then creates a fresh virtual environment, installs the generated wheel including its pinned
runtime dependencies, and verifies:

- `import autowave`;
- package/distribution version equality;
- `import AutoWave_class`;
- `import Timer_class`;
- presence of `scpi-driver-core 0.1.0.dev6`.

This clean-wheel check is separate from the editable development installation so packaging
mistakes cannot be hidden by the repository source tree.

## Version source

The installable package version is defined by `src/autowave/_version.py`. The repository
also retains the top-level `VERSION` file for project visibility. Tests require both values
to match.

Every merged repository change must continue to increment the version according to the
migration plan.
