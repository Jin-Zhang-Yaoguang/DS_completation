"""Regression v3 against v2 on downloaded public opponent action traces."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np
from kaggle_environments import make

import base_agent
import main


HERE = Path(__file__).resolve().parent
FIXTURE_DIR = HERE.parent / "v2_survival_guard" / "fixtures"
PRODUCTS = set(main.PRODUCTS)
ANIMALS = ("COW", "SHEEP", "GOOSE")
WIND_DOWN = 672


class TraceAgent:
    def __init__(self, actions):
        self.actions = actions

    def __call__(self, obs, configuration=None):
        step = int(obs.get("step", 0) or 0)
        return self.actions[min(step, len(self.actions) - 1)] or {"farmer": ["PASS"], "hands": [], "market": []}


def _animals(farm):
    result = {animal: 0 for animal in ANIMALS}
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if isinstance(tile, dict) and tile.get("animal") in result:
                result[tile["animal"]] += 1
    return result


def _inventory(obs, seat):
    private = obs.get("private", {}) or {}
    total = sum(max(0, int(value or 0)) for item, value in (private.get("shed", {}) or {}).items() if item in PRODUCTS)
    for inventory in private.get("inventories", []) or []:
        total += sum(max(0, int(value or 0)) for item, value in (inventory or {}).items() if item in PRODUCTS)
    for row in obs["farms"][seat].get("tiles", []) or []:
        for tile in row or []:
            if isinstance(tile, dict):
                item = tile.get("crop") or main.PRODUCT_FROM_ANIMAL.get(tile.get("animal"))
                if item in PRODUCTS:
                    total += max(0, int(tile.get("yield_units", 0) or 0))
    return total


def _run(fixture, kind, weights):
    seat = int(fixture["our_seat"])
    if kind == "v3":
        main.MODEL_FILE = Path(weights)
        main._POLICY = main.NumpyPolicy(weights)
        main._POLICY_ERROR = None
        candidate = main.agent
    else:
        candidate = base_agent.agent
    trace = TraceAgent(fixture["opponent_actions"])
    agents = [candidate, trace] if seat == 0 else [trace, candidate]
    env = make("kaggriculture", configuration={"seed": int(fixture["seed"])}, debug=False)
    steps = env.run(agents)
    assert len(steps) == 720 and [str(state.status) for state in steps[-1]] == ["DONE", "DONE"]
    animal_history = [_animals(states[seat].observation["farms"][seat]) for states in steps]
    maxima = {animal: max(row[animal] for row in animal_history[:WIND_DOWN + 1]) for animal in ANIMALS}
    early_loss = {animal: maxima[animal] - animal_history[WIND_DOWN][animal] for animal in ANIMALS}
    overflow = 0
    for states in steps:
        private = states[seat].observation.get("private", {}) or {}
        used = sum(max(0, int(value or 0)) for value in (private.get("shed", {}) or {}).values())
        overflow = max(overflow, max(0, used - 100))
    final = steps[-1]
    rewards = [float(state.reward or 0.0) for state in final]
    return {
        "reward": rewards[seat], "margin": rewards[seat] - rewards[1 - seat],
        "early_animal_loss": early_loss, "max_shed_overflow": overflow,
        "terminal_unsold": _inventory(final[seat].observation, seat),
    }


def evaluate(weights, output=None):
    fixtures = []
    for path in sorted(FIXTURE_DIR.glob("episode-*-opponent.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as source:
            fixtures.append(json.load(source))
    if not fixtures:
        raise RuntimeError("no public replay fixtures")
    rows = []
    for fixture in fixtures:
        baseline = _run(fixture, "v2", weights)
        candidate = _run(fixture, "v3", weights)
        rows.append({
            "episode_id": int(fixture["episode_id"]), "opponent": fixture["opponent"],
            "baseline": baseline, "candidate": candidate,
            "reward_delta": candidate["reward"] - baseline["reward"],
            "margin_delta": candidate["margin"] - baseline["margin"],
        })
    base_loss = sum(sum(row["baseline"]["early_animal_loss"].values()) for row in rows)
    candidate_loss = sum(sum(row["candidate"]["early_animal_loss"].values()) for row in rows)
    result = {
        "schema": "kaggriculture-v3-replay-regression-1",
        "fixtures": len(rows),
        "total_reward_delta": float(sum(row["reward_delta"] for row in rows)),
        "total_margin_delta": float(sum(row["margin_delta"] for row in rows)),
        "animal_loss": {"v2": base_loss, "v3": candidate_loss},
        "max_shed_overflow": {
            "v2": max(row["baseline"]["max_shed_overflow"] for row in rows),
            "v3": max(row["candidate"]["max_shed_overflow"] for row in rows),
        },
        "terminal_unsold": {
            "v2": int(sum(row["baseline"]["terminal_unsold"] for row in rows)),
            "v3": int(sum(row["candidate"]["terminal_unsold"] for row in rows)),
        },
        "rows": rows,
    }
    result["gates"] = {
        "reward_not_lower": result["total_reward_delta"] >= 0,
        "animal_loss_not_worse": candidate_loss <= base_loss,
        "overflow_not_worse": result["max_shed_overflow"]["v3"] <= result["max_shed_overflow"]["v2"],
        "terminal_unsold_not_worse": result["terminal_unsold"]["v3"] <= result["terminal_unsold"]["v2"],
    }
    if output:
        Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, default=HERE / "policy_weights.npz")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.weights, args.output), ensure_ascii=False, indent=2))
