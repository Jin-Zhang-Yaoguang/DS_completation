"""Leakage-safe infrastructure for periodic selective superblends.

The package is deliberately split into audit, fold generation, transforms and
selection primitives.  Importing it never scans the repository or starts an
experiment.
"""

from .registry import SNAPSHOT_SCHEMA_VERSION, RegistryError

__all__ = ["SNAPSHOT_SCHEMA_VERSION", "RegistryError"]

