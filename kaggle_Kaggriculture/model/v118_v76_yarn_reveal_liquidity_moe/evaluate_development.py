#!/usr/bin/env python3
"""Development-only dual-seat screen on deterministic Replay shop scenarios."""

from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
FACTORY = MODEL / "v10_replay_lolo_router"
ARENA = MODEL / "v116_heuristic_gold_search/replay_arena"
SOURCE = PROJECT / "model_data/failure_pattern_diagnostics_20260831/enriched_games.csv"
sys.path[:0] = [str(FACTORY), str(ARENA)]

from agent_factory import Registry, create_agent  # noqa: E402
from scenario_runner import ScenarioRunner  # noqa: E402


CANDIDATE = Path(os.environ.get("V118_CANDIDATE", HERE / "main.py")).resolve()
PARENT = MODEL / "v76_adjacent_safe_buy_lead/main.py"


def _rank(row: dict[str, str], salt: str) -> str:
    return hashlib.sha256(f"{salt}\0{row['episode_id']}".encode()).hexdigest()


def _select() -> list[tuple[str, dict[str, str], int]]:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    target = sorted(
        (row for row in rows if int(float(row["yarn_position"])) in (2, 3)),
        key=lambda row: _rank(row, "v118-development-target-v1"),
    )[:32]
    used = {row["episode_id"] for row in target}
    random = sorted(
        (row for row in rows if row["episode_id"] not in used),
        key=lambda row: _rank(row, "v118-development-random-v1"),
    )[:32]
    return [
        (panel, row, seat)
        for panel, panel_rows in (("target", target), ("random", random))
        for row in panel_rows
        for seat in (0, 1)
    ]


def _play(task: tuple[str, dict[str, str], int]) -> dict[str, object]:
    panel, row, seat = task
    registry = Registry(path=HERE / "development_registry.json", models={}, raw={})
    episode_id = int(row["episode_id"])
    candidate = create_agent(registry, {
        "id": f"candidate_{episode_id}_{seat}_{os.getpid()}",
        "kind": "python", "path": str(CANDIDATE), "entrypoint": "agent",
    })
    parent = create_agent(registry, {
        "id": f"parent_{episode_id}_{seat}_{os.getpid()}",
        "kind": "python", "path": str(PARENT), "entrypoint": "agent",
    })
    agents = [None, None]
    agents[seat], agents[1 - seat] = candidate, parent
    schedule = [
        {"shop": shop, "visible_from_step": int(step)}
        for shop, step in zip(
            row["shop_sequence"].split(">"),
            row["unlock_steps"].split(">"),
        )
    ]
    result = ScenarioRunner(
        int(float(row["seed"])), agents[0], agents[1], schedule, 720
    ).run()
    own = float(result.rewards[seat])
    rival = float(result.rewards[1 - seat])
    return {
        "panel": panel, "episode_id": episode_id, "seat": seat,
        "yarn_position": int(float(row["yarn_position"])),
        "candidate_reward": own, "parent_reward": rival, "margin": own - rival,
        "steps": result.steps,
    }


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    wins = sum(float(row["margin"]) > 0 for row in rows)
    ties = sum(float(row["margin"]) == 0 for row in rows)
    losses = len(rows) - wins - ties
    return {
        "sources": len(rows) // 2, "games": len(rows),
        "wins_ties_losses": [wins, ties, losses],
        "score_rate": (wins + 0.5 * ties) / len(rows),
        "mean_margin": statistics.mean(float(row["margin"]) for row in rows),
        "all_720_steps": all(int(row["steps"]) == 719 for row in rows),
    }


def main() -> int:
    tasks = _select()
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(12, os.cpu_count() or 1)
    ) as pool:
        rows = list(pool.map(_play, tasks, chunksize=1))
    result = {
        "schema": "v118-development-screen-v1",
        "data_role": "development_only_not_final_gate",
        "source_class": "ACCOUNT_ONLINE",
        "historical_actions_used_by_arena": False,
        "panels": {
            panel: _summary([row for row in rows if row["panel"] == panel])
            for panel in ("target", "random")
        },
        "rows": rows,
    }
    (HERE / "development_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"panels": result["panels"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
