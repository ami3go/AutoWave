"""Public package namespace for the AutoWave driver migration.

The production driver API is introduced incrementally by the migration plan.
The legacy top-level AutoWave_class module remains packaged for compatibility
until its facade is replaced in later migration phases.
"""

from autowave._version import __version__

__all__ = ["__version__"]
