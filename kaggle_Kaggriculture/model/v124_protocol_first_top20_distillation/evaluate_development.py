#!/usr/bin/env python3
"""Gate 2：V124 对已知 V120 与 V21/V29/V76 家族的双席位开发筛查。"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any


HERE = Path(__file__).resolve().parent
KAGGRICULTURE = HERE.parents[1]
MODEL = KAGGRICULTURE / "model"
FACTORY = MODEL / "v10_replay_lolo_router"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path[:0] = [str(FACTORY), str(CPPSIM)]

import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402


CANDIDATE = HERE / "main.py"
CANDIDATE_DEPENDENCIES = (HERE / "contract.py", HERE / "train_hmoe.py", HERE / "training/contract_hmoe.joblib")
OPPONENTS = {
    "V120_REGRESSION": MODEL / "v120_hierarchical_top5_distillation/main.py",
    "V21_V29_V76_KNOWN_FAMILY": MODEL / "v21_top_meta_moe/main.py",
}
SEED_LABEL = "v124-gate2-known-development-r0-20260902"
SEEDS = (
    1822420706, 52660388, 1623554723, 593749170,
    582599467, 1305351051, 1972832203, 405605251,
    1451149527, 1550040316, 113525993, 2087234847,
    1733497537, 1015788237, 1495453852, 964600184,
)
OUT = HERE / "development"
GAMES = OUT / "games.jsonl"
MANIFEST = OUT / "run_manifest.json"
REPORT = OUT / "development_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def task_key(row: dict) -> tuple[str, int, int]:
    return str(row["opponent"]), int(row["seed"]), int(row["candidate_seat"])


def play(task: tuple[str, int, int]) -> dict[str, Any]:
    opponent_name, seed, candidate_seat = task
    base = {"opponent": opponent_name, "seed": seed, "candidate_seat": candidate_seat}
    started = time.perf_counter()
    try:
        registry = Registry(path=OUT / "registry.json", models={}, raw={})
        candidate = create_agent(registry, {
            "id": f"v124_{opponent_name}_{seed}_{candidate_seat}_{os.getpid()}",
            "kind": "python", "path": str(CANDIDATE), "entrypoint": "agent",
        })
        opponent = create_agent(registry, {
            "id": f"known_{opponent_name}_{seed}_{candidate_seat}_{os.getpid()}",
            "kind": "python", "path": str(OPPONENTS[opponent_name]), "entrypoint": "agent",
        })
        agents = [opponent, opponent]
        agents[candidate_seat] = candidate
        game = kagsim.Game(seed)
        calls = 0
        while not game.done:
            game.step(agents[0](game.observe(0)), agents[1](game.observe(1)))
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        own, rival = rewards[candidate_seat], rewards[1 - candidate_seat]
        margin = own - rival
        return {
            **base, "status": "DONE", "error": None, "calls": calls,
            "candidate_reward": own, "opponent_reward": rival, "margin": margin,
            "outcome": "win" if margin > 0 else "tie" if margin == 0 else "loss",
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    except Exception as exc:
        return {
            **base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}",
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }


def wilson(wins: int, games: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = wins / games if games else 0.0
    denominator = 1 + z * z / max(1, games)
    center = (p + z * z / (2 * max(1, games))) / denominator
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * max(1, games))) / max(1, games)) / denominator
    return center - half, center + half


def load_completed() -> tuple[list[dict], set[tuple[str, int, int]]]:
    rows: list[dict] = []
    keys: set[tuple[str, int, int]] = set()
    if not GAMES.exists():
        return rows, keys
    for line in GAMES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = task_key(row)
        if key in keys:
            raise RuntimeError(f"重复对局: {key}")
        rows.append(row)
        keys.add(key)
    return rows, keys


def aggregate(rows: list[dict], elapsed: float) -> dict:
    matchups: list[dict] = []
    for opponent in OPPONENTS:
        values = [row for row in rows if row["opponent"] == opponent]
        done = [row for row in values if row["status"] == "DONE"]
        errors = [row for row in values if row["status"] != "DONE"]
        wins = sum(row["outcome"] == "win" for row in done)
        ties = sum(row["outcome"] == "tie" for row in done)
        losses = sum(row["outcome"] == "loss" for row in done)
        seat_rows = {seat: [row for row in done if row["candidate_seat"] == seat] for seat in (0, 1)}
        matchups.append({
            "opponent": opponent,
            "games_expected": len(SEEDS) * 2,
            "games_done": len(done),
            "wins_ties_losses_errors": [wins, ties, losses, len(errors)],
            "pure_win_rate": wins / (len(SEEDS) * 2),
            "wilson95": list(wilson(wins, len(SEEDS) * 2)),
            "score_rate": (wins + 0.5 * ties) / (len(SEEDS) * 2),
            "seat0_win_rate": sum(row["outcome"] == "win" for row in seat_rows[0]) / len(SEEDS),
            "seat1_win_rate": sum(row["outcome"] == "win" for row in seat_rows[1]) / len(SEEDS),
            "mean_candidate_reward": statistics.mean(row["candidate_reward"] for row in done) if done else None,
            "mean_opponent_reward": statistics.mean(row["opponent_reward"] for row in done) if done else None,
            "mean_margin": statistics.mean(row["margin"] for row in done) if done else None,
            "all_719_calls": len(done) == len(SEEDS) * 2 and all(row["calls"] == 719 for row in done),
        })
    errors = [row for row in rows if row["status"] != "DONE"]
    complete = all(item["games_done"] == len(SEEDS) * 2 and item["all_719_calls"] for item in matchups) and not errors
    strength_pass = all(item["pure_win_rate"] >= 0.50 for item in matchups)
    return {
        "schema": "kaggriculture-v124-gate2-development-v1",
        "status": "GATE2_PASS" if complete and strength_pass else "GATE2_FAIL",
        "candidate": "V124-R0",
        "engine": str(kagsim.ENGINE_VERSION),
        "seed_label": SEED_LABEL,
        "seeds": list(SEEDS),
        "protocol": {
            "known_only": True,
            "dual_seat": True,
            "games_per_family": len(SEEDS) * 2,
            "acceptance_predeclared": "zero errors, all 719 calls, and pure win rate >=50% independently against both known families",
            "promotion_evidence": False,
            "V21_V29_V76_count_as_one_family": True,
        },
        "elapsed_seconds": elapsed,
        "completed_games": sum(row["status"] == "DONE" for row in rows),
        "error_count": len(errors),
        "matchups": matchups,
        "failure_action": "candidate may be revised with a new SHA and must rerun Gate 0/1; Gate 3 remains unopened",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if str(kagsim.ENGINE_VERSION) != ENGINE:
        raise RuntimeError(f"引擎版本漂移: {kagsim.ENGINE_VERSION}")
    files = (CANDIDATE, *CANDIDATE_DEPENDENCIES, *OPPONENTS.values())
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(missing)
    manifest = {
        "schema": "kaggriculture-v124-gate2-run-manifest-v1",
        "candidate": {
            "name": "V124-R0",
            "files": {str(path.relative_to(HERE)): sha256(path) for path in (CANDIDATE, *CANDIDATE_DEPENDENCIES)},
        },
        "opponents": {name: {"path": str(path), "sha256": sha256(path)} for name, path in OPPONENTS.items()},
        "engine": str(kagsim.ENGINE_VERSION),
        "seed_label": SEED_LABEL,
        "seeds": list(SEEDS),
        "expected_games": len(OPPONENTS) * len(SEEDS) * 2,
    }
    if MANIFEST.exists():
        if json.loads(MANIFEST.read_text(encoding="utf-8")) != manifest:
            raise RuntimeError("Gate 2 清单漂移，拒绝混合续跑")
    else:
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows, completed = load_completed()
    tasks = [
        (opponent, seed, seat)
        for opponent in OPPONENTS for seed in SEEDS for seat in (0, 1)
        if (opponent, seed, seat) not in completed
    ]
    print(json.dumps({"status": "STARTING", "remaining": len(tasks), "workers": args.workers}, ensure_ascii=False), flush=True)
    started = time.perf_counter()
    mode = "a" if GAMES.exists() else "w"
    if tasks:
        with GAMES.open(mode, encoding="utf-8") as handle, mp.Pool(args.workers) as pool:
            for index, row in enumerate(pool.imap_unordered(play, tasks, chunksize=1), 1):
                rows.append(row)
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                if index % 16 == 0 or index == len(tasks):
                    print(json.dumps({"completed": len(completed) + index, "total": len(OPPONENTS) * len(SEEDS) * 2}, ensure_ascii=False), flush=True)
    report = aggregate(rows, time.perf_counter() - started)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "matchups": report["matchups"]}, ensure_ascii=False, indent=2), flush=True)
    return 0 if report["status"] == "GATE2_PASS" else 2


ENGINE = "1.32.7"


if __name__ == "__main__":
    raise SystemExit(main())
