#!/usr/bin/env python3
"""Strict pure-win RC2 gates: 64 Replay sources x both seats per panel."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
FACTORY = MODEL / "v10_replay_lolo_router"
ARENA = MODEL / "v116_heuristic_gold_search/replay_arena"
WHITELIST = MODEL / "v117_state_contract_daily_option_hmoe/replay_data"
sys.path[:0] = [str(FACTORY), str(ARENA), str(WHITELIST)]

from agent_factory import Registry, create_agent  # noqa: E402
from scenario_runner import ScenarioRunner  # noqa: E402
from stream_whitelist import read_replay_whitelist  # noqa: E402


MANIFEST = HERE / "gate_panel_manifest_rc2.json"
CANDIDATE = HERE / "main.py"
PARENT = MODEL / "v76_adjacent_safe_buy_lead/main.py"
OUTPUT = HERE / "frozen_gate_results_rc2.json"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _unlocks(shops_by_step: tuple[tuple[str, ...], ...]) -> list[dict[str, Any]]:
    prior: tuple[str, ...] = ()
    rows: list[dict[str, Any]] = []
    for step, shops in enumerate(shops_by_step):
        if shops == prior:
            continue
        if len(shops) < len(prior) or shops[:len(prior)] != prior:
            raise ValueError(f"non-monotone shop sequence at step {step}")
        for ordinal, shop in enumerate(shops[len(prior):], start=len(prior) + 1):
            rows.append({"ordinal": ordinal, "shop": shop, "visible_from_step": step})
        prior = shops
    return rows


def _verify_assignment(task: tuple[dict[str, Any], str, str]) -> dict[str, Any]:
    row, expected_module, expected_config_sha = task
    path = Path(row["replay_path"])
    if _file_sha256(path) != row["replay_sha256"]:
        raise PermissionError(f"replay hash changed: {row['episode_id']}")
    replay = read_replay_whitelist(path, include_steps=True)
    config_sha = _canonical(replay.configuration)
    if replay.episode_id != int(row["episode_id"]):
        raise ValueError("episode id drift")
    if replay.seed != int(row["actual_seed"]):
        raise ValueError("seed drift")
    if replay.module_version != expected_module:
        raise ValueError("module drift")
    if config_sha != expected_config_sha:
        raise ValueError("configuration drift")
    schedule = _unlocks(replay.shops_by_step or ())
    if schedule != row["realized_public_shops"]:
        raise ValueError(f"shop schedule drift: {row['episode_id']}")
    scenario_sha = _canonical({
        "module_version": replay.module_version,
        "configuration_sha256": config_sha,
        "actual_seed": replay.seed,
        "realized_public_shops": schedule,
    })
    if scenario_sha != row["scenario_sha256"]:
        raise ValueError(f"scenario hash drift: {row['episode_id']}")
    if row["panel"] == "target_yarn_2_or_3":
        yarn = next(item["ordinal"] for item in schedule if item["shop"] == "YARN_STORE")
        if yarn not in (2, 3):
            raise ValueError("target panel contains non-target scenario")
    return row


def _preflight(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    lock = manifest.get("candidate_lock") or {}
    candidate_sha = _file_sha256(CANDIDATE)
    if lock.get("status") != "LOCKED" or lock.get("main_sha256") != candidate_sha:
        raise PermissionError("candidate hash does not match frozen lock")
    parent_sha = _file_sha256(PARENT)
    if lock.get("parent_main_sha256") != parent_sha:
        raise PermissionError("V76 parent hash does not match frozen lock")
    all_assignments = [dict(row) for row in manifest.get("assignments", [])]
    assignments = [row for row in all_assignments if row.get("split") == "frozen_gate"]
    counts = {
        panel: sum(row["panel"] == panel for row in assignments)
        for panel in ("target_yarn_2_or_3", "random")
    }
    if counts != {"target_yarn_2_or_3": 64, "random": 64}:
        raise ValueError(f"frozen panel count drift: {counts}")
    verification_tasks = [
        (row, manifest["expected_module_version"], manifest["expected_configuration_sha256"])
        for row in all_assignments
    ]
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(12, os.cpu_count() or 1)
    ) as pool:
        verified = list(pool.map(_verify_assignment, verification_tasks, chunksize=1))
    for key in ("episode_id", "actual_seed", "scenario_sha256"):
        values = [row[key] for row in verified]
        if len(values) != len(set(values)):
            raise ValueError(f"development/frozen isolation collision: {key}")
    return [row for row in verified if row.get("split") == "frozen_gate"]


def _play(task: tuple[dict[str, Any], int]) -> dict[str, Any]:
    row, seat = task
    episode_id = int(row["episode_id"])
    registry = Registry(path=HERE / "frozen_registry.json", models={}, raw={})
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
    result = ScenarioRunner(
        int(row["actual_seed"]), agents[0], agents[1],
        row["realized_public_shops"], 720,
    ).run()
    own = float(result.rewards[seat])
    rival = float(result.rewards[1 - seat])
    return {
        "panel": row["panel"], "episode_id": episode_id, "seat": seat,
        "yarn_position": int(row["yarn_position"]),
        "candidate_reward": own, "v76_reward": rival,
        "margin": own - rival, "steps": result.steps,
    }


def _summarize(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    wins = sum(row["margin"] > 0 for row in rows)
    ties = sum(row["margin"] == 0 for row in rows)
    losses = len(rows) - wins - ties
    pure_rate = wins / len(rows)
    score_rate = (wins + 0.5 * ties) / len(rows)
    return {
        "sources": len(rows) // 2, "games": len(rows),
        "wins_ties_losses": [wins, ties, losses],
        "pure_win_rate": pure_rate,
        "score_rate": score_rate,
        "mean_margin": statistics.mean(row["margin"] for row in rows),
        "threshold": threshold, "pass": pure_rate >= threshold,
        "all_719_agent_steps": all(row["steps"] == 719 for row in rows),
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("frozen gate output already exists; refusing a repeated look")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assignments = _preflight(manifest)
    tasks = [(row, seat) for row in assignments for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(12, os.cpu_count() or 1)
    ) as pool:
        rows = list(pool.map(_play, tasks, chunksize=1))
    target = _summarize(
        [row for row in rows if row["panel"] == "target_yarn_2_or_3"], 0.80
    )
    random = _summarize([row for row in rows if row["panel"] == "random"], 0.55)
    result = {
        "schema": "v118-frozen-gate-results-rc2-v1",
        "manifest_sha256": _file_sha256(MANIFEST),
        "candidate_main_sha256": _file_sha256(CANDIDATE),
        "parent": "v76_adjacent_safe_buy_lead",
        "parent_main_sha256": _file_sha256(PARENT),
        "engine": "1.32.7",
        "source_class": "ACCOUNT_ONLINE",
        "source_results_mixed": False,
        "replay_fields_materialized": "public shops only",
        "historical_player_actions_used": False,
        "gate_metric": "pure_win_rate; ties are not wins",
        "panels": {"target_yarn_2_or_3": target, "random": random},
        "pass": target["pass"] and random["pass"],
        "rows": rows,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": result["panels"], "pass": result["pass"]}, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
