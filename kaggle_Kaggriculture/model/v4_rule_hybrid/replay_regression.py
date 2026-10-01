"""在已有公开对手动作夹具上比较最终 V4 与 V2。"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from kaggle_environments import make

import base_agent
import main


HERE = Path(__file__).resolve().parent
FIXTURE_DIR = HERE.parent / "v2_survival_guard" / "fixtures"
PRODUCTS = {
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
}
ANIMALS = ("COW", "SHEEP", "GOOSE")
WIND_DOWN = 672


class TraceAgent:
    def __init__(self, actions):
        self.actions = actions

    def __call__(self, obs, configuration=None):
        del configuration
        step = int(obs.get("step", 0) or 0)
        return self.actions[min(step, len(self.actions) - 1)] or {
            "farmer": ["PASS"], "hands": [], "market": [],
        }


def _animals(farm):
    result = {animal: 0 for animal in ANIMALS}
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if isinstance(tile, dict) and tile.get("animal") in result:
                result[tile["animal"]] += 1
    return result


def _terminal_unsold(obs, seat):
    private = obs.get("private", {}) or {}
    total = sum(
        max(0, int(value or 0))
        for item, value in (private.get("shed", {}) or {}).items()
        if item in PRODUCTS
    )
    for inventory in private.get("inventories", []) or []:
        total += sum(
            max(0, int(value or 0))
            for item, value in (inventory or {}).items()
            if item in PRODUCTS
        )
    return total


def _run(fixture, candidate):
    seat = int(fixture["our_seat"])
    trace = TraceAgent(fixture["opponent_actions"])
    agents = [candidate, trace] if seat == 0 else [trace, candidate]
    env = make("kaggriculture", configuration={"seed": int(fixture["seed"])}, debug=False)
    steps = env.run(agents)
    assert len(steps) == 720
    assert [str(state.status) for state in steps[-1]] == ["DONE", "DONE"]
    history = [_animals(states[seat].observation["farms"][seat]) for states in steps]
    maxima = {animal: max(row[animal] for row in history[: WIND_DOWN + 1]) for animal in ANIMALS}
    early_loss = {animal: maxima[animal] - history[WIND_DOWN][animal] for animal in ANIMALS}
    overflow = 0
    for states in steps:
        private = states[seat].observation.get("private", {}) or {}
        used = sum(max(0, int(value or 0)) for value in (private.get("shed", {}) or {}).values())
        overflow = max(overflow, max(0, used - 100))
    final = steps[-1]
    rewards = [float(state.reward or 0) for state in final]
    return {
        "reward": rewards[seat],
        "margin": rewards[seat] - rewards[1 - seat],
        "early_animal_loss": early_loss,
        "max_shed_overflow": overflow,
        "terminal_unsold": _terminal_unsold(final[seat].observation, seat),
    }


def evaluate():
    rows = []
    for path in sorted(FIXTURE_DIR.glob("episode-*-opponent.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as source:
            fixture = json.load(source)
        baseline = _run(fixture, base_agent.agent)
        candidate = _run(fixture, main.make_agent("r4"))
        rows.append({
            "episode_id": int(fixture["episode_id"]),
            "opponent": fixture["opponent"],
            "baseline": baseline,
            "candidate": candidate,
            "reward_delta": candidate["reward"] - baseline["reward"],
            "margin_delta": candidate["margin"] - baseline["margin"],
        })
    base_loss = sum(sum(row["baseline"]["early_animal_loss"].values()) for row in rows)
    candidate_loss = sum(sum(row["candidate"]["early_animal_loss"].values()) for row in rows)
    result = {
        "schema": "kaggriculture-v4-replay-regression-1",
        "fixtures": len(rows),
        "total_reward_delta": float(sum(row["reward_delta"] for row in rows)),
        "total_margin_delta": float(sum(row["margin_delta"] for row in rows)),
        "animal_loss": {"v2": base_loss, "v4": candidate_loss},
        "max_shed_overflow": {
            "v2": max(row["baseline"]["max_shed_overflow"] for row in rows),
            "v4": max(row["candidate"]["max_shed_overflow"] for row in rows),
        },
        "terminal_unsold": {
            "v2": int(sum(row["baseline"]["terminal_unsold"] for row in rows)),
            "v4": int(sum(row["candidate"]["terminal_unsold"] for row in rows)),
        },
        "rows": rows,
    }
    result["gates"] = {
        "reward_not_lower": result["total_reward_delta"] >= 0,
        "animal_loss_not_worse": candidate_loss <= base_loss,
        "overflow_not_worse": result["max_shed_overflow"]["v4"] <= result["max_shed_overflow"]["v2"],
        "terminal_unsold_not_worse": result["terminal_unsold"]["v4"] <= result["terminal_unsold"]["v2"],
    }
    (HERE / "replay_regression_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    evaluate()
