#!/usr/bin/env python3
"""Run V118 against the frozen Gold-18 pool on two independent panels."""

from __future__ import annotations

from collections import Counter, defaultdict
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
V118 = HERE.parent
MODEL = V118.parent
PROJECT = MODEL.parent
BASE = PROJECT / "model_data/round_robin/gold18_replay_admitted_128x2_20260830"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(CPPSIM)]

import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402


CANDIDATE = V118 / "main.py"
EXPECTED_CANDIDATE_SHA = "4cbfa37aa19463979b7e3a23ccb8d6db0664285b1afb32df27b971f1ccfea71d"
BASE_RUN = BASE / "run_manifest.json"
PANEL_FILES = {
    "account_online": HERE / "account_panel.json",
    "official_daily": BASE / "official_panel.json",
}
MANIFEST = HERE / "run_manifest.json"
GAMES = HERE / "games.jsonl"
SUMMARY = HERE / "summary.json"
WORKERS = min(16, os.cpu_count() or 1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_shops(source: dict[str, Any], step: int) -> list[str]:
    return [shop for shop, unlock in zip(source["shops"], source["unlock_steps"]) if int(unlock) <= step]


def task_key(row: dict[str, Any]) -> tuple[str, str, int, str]:
    return str(row["panel"]), str(row["opponent"]), int(row["candidate_seat"]), str(row["source_id"])


def load_pool() -> dict[str, Path]:
    base = json.loads(BASE_RUN.read_text(encoding="utf-8"))
    pool: dict[str, Path] = {}
    for model, spec in base["models"].items():
        path = PROJECT / spec["path"]
        if sha256(path) != spec["sha256"]:
            raise PermissionError(f"Gold-18 source hash drift: {model}")
        pool[model] = path
    if len(pool) != 18:
        raise ValueError(f"expected 18 gold-pool models, got {len(pool)}")
    return pool


def panel_rows(path: Path) -> list[dict[str, Any]]:
    panel = json.loads(path.read_text(encoding="utf-8"))
    rows = list(panel["final_test"])
    if len(rows) != 128:
        raise ValueError(f"panel {path} has {len(rows)} final rows")
    return rows


def preflight(pool: dict[str, Path], panels: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    checks = {
        "engine_1_32_7": str(kagsim.ENGINE_VERSION) == "1.32.7",
        "candidate_hash_exact": sha256(CANDIDATE) == EXPECTED_CANDIDATE_SHA,
        "gold18_sources_hash_locked": len(pool) == 18,
        "two_panels_128_each": set(panels) == set(PANEL_FILES) and all(len(rows) == 128 for rows in panels.values()),
        "all_after_cutoff": all(row["date"] >= "2026-08-20" for rows in panels.values() for row in rows),
        "module_exact": all(row["module_version"] == "1.32.7" for rows in panels.values() for row in rows),
        "configuration_exact": all(
            row["configuration_sha256"] == "1a9006518ccbe403a70e107bb041cc2489e38da637ae0e3872500010963c46f3"
            for rows in panels.values() for row in rows
        ),
        "historical_actions_results_market_excluded": all(
            not row["historical_actions_included"]
            and not row["historical_rewards_included"]
            and not row["historical_market_inventory_included"]
            for rows in panels.values() for row in rows
        ),
    }
    account, official = panels["account_online"], panels["official_daily"]
    checks.update({
        "cross_panel_episode_isolation": not ({row["episode_id"] for row in account} & {row["episode_id"] for row in official}),
        "cross_panel_seed_isolation": not ({row["seed"] for row in account} & {row["seed"] for row in official}),
        "cross_panel_scenario_isolation": not ({row["scenario_sha256"] for row in account} & {row["scenario_sha256"] for row in official}),
    })
    empty = {"farmer": ["PASS"], "hands": [], "market": []}
    observations_checked = 0
    parity_errors = []
    for panel, rows in panels.items():
        for source in rows:
            game = kagsim.Game(int(source["seed"]), source["shops"], source["unlock_steps"])
            while True:
                got = list(game.observe(0)["town"]["unlocked_shops"])
                want = expected_shops(source, game.step_count)
                observations_checked += 1
                if got != want:
                    parity_errors.append({"panel": panel, "episode_id": source["episode_id"], "step": game.step_count})
                    break
                if game.done:
                    break
                game.step(empty, empty)
    checks["forced_shop_trajectory_exact"] = not parity_errors
    checks["all_256_scenarios_checked_720_steps"] = observations_checked == 256 * 720
    result = {
        "schema": "kaggriculture-v118-gold-registration-preflight-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "observations_checked": observations_checked,
        "checks": checks,
        "parity_errors": parity_errors[:20],
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    (HERE / "preflight_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise RuntimeError(f"preflight failed: {result}")
    return result


POOL = load_pool()


def play(task: tuple[str, str, int, dict[str, Any]]) -> dict[str, Any]:
    panel, opponent, candidate_seat, source = task
    base = {
        "panel": panel, "opponent": opponent, "candidate_seat": candidate_seat,
        "source_id": str(source["episode_id"]), "seed": int(source["seed"]),
        "date": source["date"], "first_shop": source["first_shop"],
        "scenario_sha256": source["scenario_sha256"],
    }
    started = time.perf_counter()
    try:
        registry = Registry(path=HERE / "registry.json", models={}, raw={})
        candidate = create_agent(registry, {
            "id": f"v118_{panel}_{opponent}_{candidate_seat}_{source['episode_id']}_{os.getpid()}",
            "kind": "python", "path": str(CANDIDATE), "entrypoint": "agent",
        })
        rival = create_agent(registry, {
            "id": f"rival_{panel}_{opponent}_{candidate_seat}_{source['episode_id']}_{os.getpid()}",
            "kind": "python", "path": str(POOL[opponent]), "entrypoint": "agent",
        })
        agents = [rival, rival]
        agents[candidate_seat] = candidate
        game = kagsim.Game(int(source["seed"]), source["shops"], source["unlock_steps"])
        calls = 0
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            if observations[0]["town"]["unlocked_shops"] != expected_shops(source, game.step_count):
                raise RuntimeError(f"forced shop drift at step {game.step_count}")
            game.step(agents[0](observations[0]), agents[1](observations[1]))
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        candidate_reward = rewards[candidate_seat]
        opponent_reward = rewards[1 - candidate_seat]
        margin = candidate_reward - opponent_reward
        return {
            **base, "status": "DONE", "error": None, "calls": calls,
            "candidate_reward": candidate_reward, "opponent_reward": opponent_reward,
            "candidate_margin": margin,
            "result": "win" if margin > 0 else "loss" if margin < 0 else "tie",
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    except Exception as exc:
        return {
            **base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}",
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        }


def load_completed() -> tuple[list[dict[str, Any]], set[tuple[str, str, int, str]]]:
    rows: list[dict[str, Any]] = []
    keys: set[tuple[str, str, int, str]] = set()
    if not GAMES.exists():
        return rows, keys
    for line in GAMES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = task_key(row)
        if key in keys:
            raise RuntimeError(f"duplicate existing task key: {key}")
        rows.append(row)
        keys.add(key)
    return rows, keys


def wilson(wins: int, games: int) -> list[float]:
    z = 1.959963984540054
    p = wins / games
    den = 1 + z * z / games
    center = (p + z * z / (2 * games)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * games)) / games) / den
    return [center - half, center + half]


def summarize(panel: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    done = [row for row in rows if row["panel"] == panel and row["status"] == "DONE"]
    errors = [row for row in rows if row["panel"] == panel and row["status"] != "DONE"]
    wins = sum(row["candidate_margin"] > 0 for row in done)
    ties = sum(row["candidate_margin"] == 0 for row in done)
    losses = sum(row["candidate_margin"] < 0 for row in done)
    by_opponent = []
    for opponent in POOL:
        values = [row for row in done if row["opponent"] == opponent]
        ow = sum(row["candidate_margin"] > 0 for row in values)
        ot = sum(row["candidate_margin"] == 0 for row in values)
        ol = sum(row["candidate_margin"] < 0 for row in values)
        by_opponent.append({
            "opponent": opponent, "games": len(values), "wins": ow, "ties": ot, "losses": ol,
            "pure_win_rate": ow / len(values) if values else None,
            "score_rate": (ow + 0.5 * ot) / len(values) if values else None,
            "mean_margin": statistics.mean(row["candidate_margin"] for row in values) if values else None,
        })
    checks = {
        "completed_4608": len(done) == 18 * 128 * 2,
        "zero_errors": not errors,
        "each_opponent_256": all(row["games"] == 256 for row in by_opponent),
        "all_719_calls": all(row["calls"] == 719 for row in done),
        "both_seats_balanced": all(
            Counter(row["candidate_seat"] for row in done if row["opponent"] == opponent) == Counter({0: 128, 1: 128})
            for opponent in POOL
        ),
    }
    pure = wins / len(done) if done else 0.0
    return {
        "panel": panel, "games": len(done), "wins": wins, "ties": ties, "losses": losses,
        "pure_win_rate": pure, "pure_win_rate_wilson_95": wilson(wins, len(done)),
        "score_rate": (wins + 0.5 * ties) / len(done) if done else 0.0,
        "mean_margin": statistics.mean(row["candidate_margin"] for row in done) if done else None,
        "threshold": 0.75, "pass": pure >= 0.75,
        "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
        "by_opponent": by_opponent, "errors": errors[:100],
    }


def main() -> int:
    panels = {name: panel_rows(path) for name, path in PANEL_FILES.items()}
    preflight_result = preflight(POOL, panels)
    manifest = {
        "schema": "kaggriculture-v118-gold-registration-run-v1",
        "candidate": {"model": "V118", "path": str(CANDIDATE.relative_to(PROJECT)), "sha256": sha256(CANDIDATE)},
        "opponents": {model: {"path": str(path.relative_to(PROJECT)), "sha256": sha256(path)} for model, path in POOL.items()},
        "panels": {name: {"path": str(PANEL_FILES[name].relative_to(PROJECT)), "sha256": sha256(PANEL_FILES[name]), "sources": 128} for name in PANEL_FILES},
        "engine": str(kagsim.ENGINE_VERSION), "workers": WORKERS,
        "protocol": {
            "games_per_opponent_per_panel": 256,
            "games_per_panel": 4608,
            "strict_pure_win_rate": True,
            "ties_are_not_wins": True,
            "gold_gate": "account pure_win_rate >= 0.75 AND official pure_win_rate >= 0.75",
            "historical_actions_used": False,
        },
        "preflight_sha256": sha256(HERE / "preflight_results.json"),
        "expected_games": 9216,
    }
    if MANIFEST.exists():
        if json.loads(MANIFEST.read_text(encoding="utf-8")) != manifest:
            raise RuntimeError("run manifest drifted; refusing mixed state")
    else:
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows, completed = load_completed()
    tasks = [
        (panel, opponent, seat, source)
        for panel, sources in panels.items()
        for opponent in POOL
        for seat in (0, 1)
        for source in sources
        if (panel, opponent, seat, str(source["episode_id"])) not in completed
    ]
    print(json.dumps({
        "status": "STARTING" if tasks else "ALREADY_COMPLETE",
        "total": 9216, "completed_before": len(rows), "remaining": len(tasks),
        "workers": WORKERS, "preflight": preflight_result["status"],
    }, ensure_ascii=False), flush=True)
    started = time.perf_counter()
    if tasks:
        with GAMES.open("a" if GAMES.exists() else "w", encoding="utf-8") as stream, mp.Pool(WORKERS) as pool:
            for index, row in enumerate(pool.imap_unordered(play, tasks, chunksize=4), 1):
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                if index % 256 == 0:
                    stream.flush()
                if index % 1024 == 0 or index == len(tasks):
                    elapsed = time.perf_counter() - started
                    print(json.dumps({
                        "completed": len(completed) + index, "total": 9216,
                        "remaining": 9216 - len(completed) - index,
                        "rate": round(index / elapsed, 3),
                        "errors": sum(row["status"] != "DONE" for row in rows),
                    }, ensure_ascii=False), flush=True)
            stream.flush()
    elapsed = time.perf_counter() - started
    panel_results = {panel: summarize(panel, rows) for panel in PANEL_FILES}
    checks = {
        "preflight_pass": preflight_result["status"] == "PASS",
        "row_count_9216": len(rows) == 9216,
        "task_keys_unique": len({task_key(row) for row in rows}) == len(rows),
        "panel_integrity_pass": all(result["status"] == "PASS" for result in panel_results.values()),
    }
    gold_pass = all(result["pass"] for result in panel_results.values())
    result = {
        "schema": "kaggriculture-v118-gold-registration-summary-v1",
        "candidate": "V118", "candidate_sha256": sha256(CANDIDATE),
        "engine": str(kagsim.ENGINE_VERSION), "completed_games": len(rows),
        "elapsed_seconds": elapsed, "checks": checks,
        "panels": panel_results,
        "gold_gate": {
            "account_min": 0.75, "official_min": 0.75,
            "both_required": True, "ties_are_not_wins": True,
            "pass": gold_pass,
        },
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    SUMMARY.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"], "gold_pass": gold_pass,
        "account": {k: panel_results["account_online"][k] for k in ("wins", "ties", "losses", "pure_win_rate", "pass")},
        "official": {k: panel_results["official_daily"][k] for k in ("wins", "ties", "losses", "pure_win_rate", "pass")},
    }, ensure_ascii=False, indent=2), flush=True)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
