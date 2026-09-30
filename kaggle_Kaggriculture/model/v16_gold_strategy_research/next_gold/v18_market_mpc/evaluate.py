#!/usr/bin/env python3
"""Development-only screen for V18 market-only MPC.

The independent blind contract (2026-08-20..24, seeds 61000..61039) is not
encoded here and must not be opened by candidate development.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
import uuid
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
INDEX = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
V17 = HERE.parents[1] / "top_complete_portfolio" / "main.py"
sys.path.insert(0, str(HERE))
from market_mpc import EXPECTED_V17_SHA256, make_agent


DEV_REPLAYS = (
    ("2026-08-25", "Crop Dusta", 99625995),
    ("2026-08-25", "Ryo Hasegawa", 99625995),
    ("2026-08-25", "Subramanya N", 99607808),
    ("2026-08-25", "tetsuya", 99612231),
    ("2026-08-25", "Kronki", 99628290),
    ("2026-08-25", "tyz123456", 99630579),
)


def load_module(path: Path, prefix: str):
    name = f"{prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def runtime():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    sys.path.insert(0, str(builds[-1]))
    sys.path.insert(0, str(FACTORY))
    import kagsim  # type: ignore
    from agent_factory import Registry, create_agent  # type: ignore
    return kagsim, Registry(path=Path(__file__).resolve(), models={}, raw={}), create_agent


def v17_agent():
    return load_module(V17, "baseline_v17").agent


def replay_actions(day: str, team: str, episode: int) -> list[dict]:
    replay = json.loads((INDEX / f"date={day}" / "data" / f"{episode}.json").read_text())
    seat = replay["info"]["TeamNames"].index(team)
    return [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]


def replay_proxy(actions: list[dict]):
    base = load_module(MODEL / "v1_adaptive_market" / "main.py", "replay_proxy")

    def policy(obs, configuration=None):
        del configuration
        base._ACTIONS = actions
        return base._CORE_AGENT(obs)

    return policy


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] if lo == hi else values[lo] * (hi - pos) + values[hi] * (pos - lo)


def summarize(rows: list[dict], prefix: str) -> dict:
    margins = sorted(float(row[f"{prefix}_margin"]) for row in rows)
    tail = margins[:max(1, math.ceil(0.1 * len(margins)))]
    return {
        "games": len(rows),
        "score_rate": statistics.mean(score(x) for x in margins),
        "wins_ties_losses": [sum(x > 0 for x in margins), sum(x == 0 for x in margins), sum(x < 0 for x in margins)],
        "mean_margin": statistics.mean(margins),
        "margin_p10": quantile(margins, 0.1),
        "margin_cvar10": statistics.mean(tail),
    }


def cluster_ci(rows: list[dict], iterations: int = 10000) -> list[float]:
    clusters = sorted({int(row["seed"]) for row in rows})
    grouped = {seed: [row for row in rows if int(row["seed"]) == seed] for seed in clusters}
    rng = random.Random(1800327)
    draws = []
    for _ in range(iterations):
        sample = [row for _seed in (rng.choice(clusters) for _ in clusters) for row in grouped[_seed]]
        draws.append(100 * statistics.mean(row["score_delta"] for row in sample))
    draws.sort()
    return [draws[int(0.025 * iterations)], draws[min(iterations - 1, int(0.975 * iterations))]]


def _resource_fingerprint(obs: dict, seat: int) -> dict:
    farm = copy.deepcopy(obs["farms"][seat])
    farm.pop("money", None)
    return {"farm_without_money": farm, "private": copy.deepcopy(obs.get("private") or {})}


def play(agent, opponent, seed: int, seat: int, kagsim) -> tuple[float, float, list, list, dict]:
    game = kagsim.Game(seed)
    agents = [None, None]
    agents[seat], agents[1 - seat] = agent, opponent
    own_units = []
    own_non_sell_market = []
    while not game.done:
        actions = [agents[0](game.observe(0)), agents[1](game.observe(1))]
        own_action = actions[seat]
        own_units.append((copy.deepcopy(own_action.get("farmer")), copy.deepcopy(own_action.get("hands"))))
        own_non_sell_market.append([
            copy.deepcopy(order) for order in (own_action.get("market") or [])
            if not (order and order[0] == "SELL")
        ])
        game.step(actions[0], actions[1])
    rewards = [float(game.reward(0)), float(game.reward(1))]
    final_resources = _resource_fingerprint(game.observe(seat), seat)
    return rewards[seat], rewards[1 - seat], own_units, own_non_sell_market, final_resources


def result_summary(rows: list[dict], configs: dict, split: str, seed_range: list[int]) -> dict:
    output = {
        "status": f"{split.upper()}_PAIRED_MARKET_ONLY_EVIDENCE",
        "frozen_v17_sha256": EXPECTED_V17_SHA256,
        "seed_range": seed_range,
        "both_seats": True,
        "configs": configs,
        "candidates": {},
    }
    for name in configs:
        selected = [row for row in rows if row["candidate"] == name]
        baseline = summarize(selected, "base")
        treated = summarize(selected, "treated")
        by_family = {}
        for family in sorted({row["family"] for row in selected}):
            group = [row for row in selected if row["family"] == family]
            by_family[family] = {
                "games": len(group),
                "base_score_rate": statistics.mean(score(row["base_margin"]) for row in group),
                "treated_score_rate": statistics.mean(score(row["treated_margin"]) for row in group),
                "uplift_pp": 100 * statistics.mean(row["score_delta"] for row in group),
            }
        output["candidates"][name] = {
            "baseline": baseline,
            "treated": treated,
            "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in selected),
            "seed_cluster_ci95_pp": cluster_ci(selected),
            "l_to_w": sum(score(row["base_margin"]) == 0 and score(row["treated_margin"]) == 1 for row in selected),
            "w_to_l": sum(score(row["base_margin"]) == 1 and score(row["treated_margin"]) == 0 for row in selected),
            "margin_delta_mean": statistics.mean(row["treated_margin"] - row["base_margin"] for row in selected),
            "unit_command_exact_games": sum(row["unit_commands_exact"] for row in selected),
            "non_sell_market_exact_games": sum(row["non_sell_market_exact"] for row in selected),
            "terminal_resource_exact_games": sum(row["terminal_resources_exact"] for row in selected),
            "changed_games": sum(row["changed_turns"] > 0 for row in selected),
            "changed_turns": sum(row["changed_turns"] for row in selected),
            "deferred_units": sum(row["deferred_units"] for row in selected),
            "expired_due_units": sum(row["expired_due_units"] for row in selected),
            "family_equal_base_score_rate": statistics.mean(v["base_score_rate"] for v in by_family.values()),
            "family_equal_treated_score_rate": statistics.mean(v["treated_score_rate"] for v in by_family.values()),
            "worst_family_uplift_pp": min(v["uplift_pp"] for v in by_family.values()),
            "by_family": by_family,
        }
    output["rows"] = rows
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--configs")
    parser.add_argument("--output")
    args = parser.parse_args()
    actual_sha = hashlib.sha256(V17.read_bytes()).hexdigest()
    if actual_sha != EXPECTED_V17_SHA256:
        raise RuntimeError(f"V17 hash mismatch: {actual_sha}")
    default_configs = {
        "close_q5": {"lead_ceiling": 5000, "quantity_cap": 5, "shed_ceiling": 80, "cash_floor": 3000},
        "close_q20": {"lead_ceiling": 5000, "quantity_cap": 20, "shed_ceiling": 80, "cash_floor": 3000},
        "trailing_q20": {"lead_ceiling": 0, "quantity_cap": 20, "shed_ceiling": 80, "cash_floor": 3000},
        "wide_q20": {"lead_ceiling": 20000, "quantity_cap": 20, "shed_ceiling": 80, "cash_floor": 3000},
        "close_q20_room90": {"lead_ceiling": 5000, "quantity_cap": 20, "shed_ceiling": 90, "cash_floor": 3000},
    }
    configs = json.loads(Path(args.configs).read_text()) if args.configs else default_configs
    seed_start = args.seed_start if args.seed_start is not None else 50000
    if seed_start < 50000 or seed_start + args.seeds - 1 > 50999:
        raise RuntimeError("development seeds must stay inside frozen allowance 50000..50999")
    kagsim, registry, create_agent = runtime()
    del registry, create_agent
    families = [
        (f"{day}::{team}::{episode}", replay_actions(day, team, episode))
        for day, team, episode in DEV_REPLAYS
    ]
    rows = []
    for family, source in families:
        for seed in range(seed_start, seed_start + args.seeds):
            for seat in (0, 1):
                for name, config in configs.items():
                    def opponent(tag: str):
                        del tag
                        return replay_proxy(source)
                    base_own, base_opp, base_units, base_other_market, base_resources = play(v17_agent(), opponent("b"), seed, seat, kagsim)
                    candidate = make_agent(**config)
                    own, opp, treated_units, other_market, resources = play(candidate, opponent("t"), seed, seat, kagsim)
                    base_margin, treated_margin = base_own - base_opp, own - opp
                    stats = dict(candidate.market_mpc_stats)
                    rows.append({
                        "candidate": name, "family": family, "seed": seed, "seat": seat,
                        "base_own": base_own, "base_opp": base_opp, "base_margin": base_margin,
                        "treated_own": own, "treated_opp": opp, "treated_margin": treated_margin,
                        "score_delta": score(treated_margin) - score(base_margin),
                        "unit_commands_exact": base_units == treated_units,
                        "non_sell_market_exact": base_other_market == other_market,
                        "terminal_resources_exact": base_resources == resources,
                        **stats,
                    })
    result = result_summary(rows, configs, "dev", [seed_start, seed_start + args.seeds - 1])
    result["development_data_contract"] = {
        "source_date": "2026-08-25",
        "allowed_seed_range": [50000, 50999],
        "blind_source_dates_read": False,
        "blind_seed_range_read": False,
    }
    output = Path(args.output) if args.output else HERE / "dev_results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    compact = {"status": result["status"], "seed_range": result["seed_range"], "candidates": result["candidates"]}
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
