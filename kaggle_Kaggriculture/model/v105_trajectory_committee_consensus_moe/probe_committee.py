#!/usr/bin/env python3
"""Closed-loop source qualification for deterministic trajectory committees."""
from __future__ import annotations

import collections
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
REPLAYS = PROJECT / "model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
import kagsim  # type: ignore

EXPERTS = (100439801, 100501596, 100398798, 100414724, 100410172, 100458412, 100446711, 100465032)
MODES = ("expert_100439801", "committee_3", "committee_5", "committee_8")
SEEDS = tuple(range(105101, 105117))
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def route(episode: int):
    replay = json.loads((REPLAYS / f"episode-{episode}-replay.json").read_text())
    seat = replay["info"]["TeamNames"].index("lucaskna")
    return [step[seat].get("action") or {} for step in replay["steps"][1:720]]


def modal(values):
    encoded = [json.dumps(value, sort_keys=True, separators=(",", ":")) for value in values]
    # Lexical tie-break makes the committee deterministic and independent of expert ordering.
    counts = collections.Counter(encoded)
    winner = min(counts, key=lambda value: (-counts[value], value))
    return json.loads(winner)


def committee(pool_size: int):
    routes = [route(expert) for expert in EXPERTS[:pool_size]]
    sequence = []
    for step in range(719):
        actions = [candidate[step] for candidate in routes]
        hands = max(len(action.get("hands", []) or []) for action in actions)
        sequence.append({
            "farmer": modal([action.get("farmer") or ["PASS"] for action in actions]),
            "hands": [modal([(action.get("hands", []) or [])[index] if index < len(action.get("hands", []) or []) else ["PASS"] for action in actions]) for index in range(hands)],
            "market": modal([action.get("market", []) or [] for action in actions]),
        })
    return sequence


def policy(mode: str):
    if mode.startswith("expert_"):
        return route(int(mode.split("_")[1]))
    return committee(int(mode.split("_")[1]))


def normalize(action, obs):
    seat = int(obs.get("player", 0) or 0)
    expected = len(obs["farms"][seat].get("hands", []) or [])
    hands = [list(value or ["PASS"]) for value in (action.get("hands", []) or [])]
    hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": hands[:expected],
        "market": [list(value) for value in (action.get("market", []) or [])[:10]],
    }


def play(task):
    mode, family, seed, seat = task
    sequence = policy(mode)
    rival = load(OPPONENTS[family], f"v105_probe_{mode}_{family}_{seed}_{seat}_{os.getpid()}")
    game = kagsim.Game(seed)
    while not game.done:
        actions = [None, None]
        actions[seat] = normalize(sequence[game.step_count], game.observe(seat))
        actions[1 - seat] = rival.agent(game.observe(1 - seat))
        game.step(actions[0], actions[1])
    own, opponent = float(game.reward(seat)), float(game.reward(1 - seat))
    margin = own - opponent
    return {"mode": mode, "family": family, "seed": seed, "seat": seat, "own": own, "opponent": opponent, "margin": margin, "score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0, "catastrophic": margin < -10000}


def paired(rows, left, right):
    index = {(row["mode"], row["family"], row["seed"], row["seat"]): row for row in rows}
    deltas, margins = [], []
    for family in OPPONENTS:
        for seed in SEEDS:
            for seat in (0, 1):
                a, b = index[(left, family, seed, seat)], index[(right, family, seed, seat)]
                deltas.append(a["score"] - b["score"])
                margins.append(a["margin"] - b["margin"])
    return {"uplift_pp": 100 * statistics.mean(deltas), "positive_zero_negative": [sum(x > 0 for x in deltas), sum(x == 0 for x in deltas), sum(x < 0 for x in deltas)], "mean_margin_delta": statistics.mean(margins)}


def main():
    tasks = [(mode, family, seed, seat) for mode in MODES for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    scores = {mode: {"score": statistics.mean(r["score"] for r in rows if r["mode"] == mode), "catastrophic_rate": statistics.mean(r["catastrophic"] for r in rows if r["mode"] == mode)} for mode in MODES}
    comparisons = {mode: paired(rows, mode, "expert_100439801") for mode in MODES if mode != "expert_100439801"}
    qualified = [mode for mode in comparisons if comparisons[mode]["uplift_pp"] > 0 and comparisons[mode]["positive_zero_negative"][0] > comparisons[mode]["positive_zero_negative"][2] and 100 * (scores[mode]["catastrophic_rate"] - scores["expert_100439801"]["catastrophic_rate"]) <= 1]
    payload = {"schema": "kaggriculture-v105-committee-probe-v1", "status": "PASS_SOURCE_QUALIFICATION" if qualified else "REJECT_SOURCE_QUALIFICATION", "strategy_proof": False, "official_evaluation_sources_consumed": 0, "synthetic_seed_range": [min(SEEDS), max(SEEDS)], "games": len(rows), "scores": scores, "comparisons_vs_fixed_best": comparisons, "qualified_committees": qualified, "rows": rows}
    (HERE / "committee_probe.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
