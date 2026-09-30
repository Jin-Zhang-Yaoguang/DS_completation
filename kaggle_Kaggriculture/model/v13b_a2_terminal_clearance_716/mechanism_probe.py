"""Probe step-716 terminal fill on only the three already-exposed QA seeds."""

from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import random
from typing import Any

import numpy as np

from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2
from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import main as core


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "mechanism_probe_report.json"
SEEDS = (93451031, 93451032, 93451033)


class ProbeAgent:
    def __init__(self) -> None:
        self.parent = a2.make_agent()
        self.rows: list[dict[str, Any]] = []

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        parent_action = self.parent(obs, configuration)
        if int(obs.step) in (716, 717, 718):
            changed, orders, quantity = core._terminal_clearance_fill(
                parent_action, obs, 716
            )
            self.rows.append(
                {
                    "step": int(obs.step),
                    "added_orders": orders,
                    "added_quantity": quantity,
                    "changed": changed != core._canonical_action(parent_action),
                }
            )
        return parent_action


def main() -> None:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    games = []
    for seed in SEEDS:
        for seat in (0, 1):
            random.seed(seed * 104729 + seat * 1009)
            np.random.seed((seed + seat * 65537) % (2**32 - 1))
            probe = ProbeAgent()
            agents = [probe, kg.starter_agent] if seat == 0 else [kg.starter_agent, probe]
            stderr = StringIO()
            with redirect_stderr(stderr):
                steps = make(
                    "kaggriculture", configuration={"seed": seed}, debug=False
                ).run(agents)
            games.append(
                {
                    "seed": seed,
                    "seat": seat,
                    "steps": len(steps),
                    "statuses": [str(state.status) for state in steps[-1]],
                    "rows": probe.rows,
                    "stderr": stderr.getvalue(),
                }
            )
    total_added_orders = sum(
        row["added_orders"] for game in games for row in game["rows"]
    )
    total_added_quantity = sum(
        row["added_quantity"] for game in games for row in game["rows"]
    )
    report = {
        "schema": "kaggriculture-v13b-terminal-716-mechanism-probe-1",
        "candidate": "v13b_a2_terminal_clearance_716",
        "parent": "v12a2_no_shop_gate",
        "qa_seeds_are_previously_exposed": True,
        "validation_or_new_panel_accessed": False,
        "steps_probed": [716, 717, 718],
        "games": games,
        "total_added_orders": total_added_orders,
        "total_added_quantity": total_added_quantity,
        "operationally_distinct_from_a2": total_added_orders > 0,
        "decision": (
            "KEEP_FOR_SCREEN"
            if total_added_orders > 0
            else "REJECT_BEFORE_PACKAGING_EQUIVALENT_ON_EXPOSED_QA"
        ),
        "archive_built": False,
        "registry_activated": False,
    }
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
