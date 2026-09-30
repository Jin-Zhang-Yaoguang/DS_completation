"""V10 replay/LOLO experiment expert catalog.

This package only registers auditable complete agents.  Evaluation and router
training live in separate modules so importing the catalog never starts work.
"""

from .expert_registry import (
    BASELINE_SPECS,
    EXPERT_SPECS,
    VARIANT_SPECS,
    ExpertSpec,
    create_agent,
    factory,
    registry_records,
    resolve_spec,
)

__all__ = [
    "BASELINE_SPECS",
    "EXPERT_SPECS",
    "VARIANT_SPECS",
    "ExpertSpec",
    "create_agent",
    "factory",
    "registry_records",
    "resolve_spec",
]
