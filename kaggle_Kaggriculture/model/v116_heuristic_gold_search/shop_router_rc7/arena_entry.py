"""Common-context Router and fixed-expert entry points for a later arena."""

from __future__ import annotations

from typing import Any

from main import GENOMES, ShopRouterExecutor


MODES = ("router", *(f"fixed_{name}" for name in GENOMES))


def build_executor(mode: str = "router") -> ShopRouterExecutor:
    if mode == "router":
        return ShopRouterExecutor()
    prefix = "fixed_"
    if mode.startswith(prefix) and mode[len(prefix):] in GENOMES:
        return ShopRouterExecutor(fixed_expert=mode[len(prefix):])
    raise ValueError(f"unsupported mode {mode!r}; expected one of {MODES}")


def make_agent(mode: str = "router") -> Any:
    return build_executor(mode).act


__all__ = ["MODES", "build_executor", "make_agent"]
