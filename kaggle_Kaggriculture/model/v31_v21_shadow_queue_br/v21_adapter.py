"""Small instance-shaped adapter around the complete frozen V21 policy."""

from __future__ import annotations

from typing import Any

import v21_parent


class V21Agent:
    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
        del configuration
        return v21_parent.agent(obs)

    @staticmethod
    def _selected_branch() -> str:
        return "v21"

    @staticmethod
    def diagnostics() -> dict[str, Any]:
        return {"kind": "v21_frozen_parent", "selected_branch": "v21"}


def make_agent() -> V21Agent:
    return V21Agent()
