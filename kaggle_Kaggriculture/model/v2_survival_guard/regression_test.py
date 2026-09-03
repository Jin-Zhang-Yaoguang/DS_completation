"""Paired regressions against action traces from the v1 public losses."""

from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path

from kaggle_environments import make


SCHEME_DIR = Path(__file__).resolve().parent
V1_PATH = SCHEME_DIR.parent / "v1_adaptive_market" / "main.py"
V2_PATH = SCHEME_DIR / "main.py"
FIXTURE_DIR = SCHEME_DIR / "fixtures"
TERMINAL_WIND_DOWN_STEP = 672


def load_agent(path: Path, label: str):
    spec = importlib.util.spec_from_file_location(label, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


class TraceAgent:
    def __init__(self, actions):
        self.actions = actions

    def __call__(self, obs, configuration=None):
        del configuration
        step = int(obs.get("step", 0) or 0)
        action = self.actions[min(step, len(self.actions) - 1)]
        return action or {"farmer": ["PASS"], "hands": [], "market": []}


def animal_counts(farm):
    counts = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if isinstance(tile, dict) and tile.get("animal") in counts:
                counts[tile["animal"]] += 1
    return counts


def run_fixture(agent_path: Path, fixture, label: str):
    seat = int(fixture["our_seat"])
    candidate = load_agent(agent_path, label)
    trace = TraceAgent(fixture["opponent_actions"])
    agents = [candidate, trace] if seat == 0 else [trace, candidate]
    env = make(
        "kaggriculture",
        configuration={"seed": int(fixture["seed"])},
        debug=False,
    )
    steps = env.run(agents)
    final = steps[-1]
    statuses = [str(state.status) for state in final]
    if statuses != ["DONE", "DONE"]:
        raise AssertionError((fixture["episode_id"], label, statuses))

    history = []
    for step_index, state in enumerate(steps):
        observation = state[seat].observation
        history.append((step_index, animal_counts(observation["farms"][seat])))
    before_wind_down = [counts for step, counts in history if step <= TERMINAL_WIND_DOWN_STEP]
    maxima = {
        animal: max(counts[animal] for counts in before_wind_down)
        for animal in ("COW", "SHEEP", "GOOSE")
    }
    at_wind_down = history[min(TERMINAL_WIND_DOWN_STEP, len(history) - 1)][1]
    early_loss = {
        animal: maxima[animal] - at_wind_down[animal]
        for animal in maxima
    }
    rewards = [float(state.reward or 0) for state in final]
    return {
        "reward": rewards[seat],
        "opponent_reward": rewards[1 - seat],
        "margin": rewards[seat] - rewards[1 - seat],
        "max_animals": maxima,
        "animals_at_wind_down": at_wind_down,
        "early_animal_loss": early_loss,
    }


def load_fixtures():
    fixtures = []
    for path in sorted(FIXTURE_DIR.glob("episode-*-opponent.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as source:
            fixtures.append(json.load(source))
    if not fixtures:
        raise AssertionError("No online replay fixtures found")
    return fixtures


def run():
    rows = []
    for fixture in load_fixtures():
        episode_id = int(fixture["episode_id"])
        baseline = run_fixture(V1_PATH, fixture, f"v1_{episode_id}")
        candidate = run_fixture(V2_PATH, fixture, f"v2_{episode_id}")
        rows.append(
            {
                "episode_id": episode_id,
                "opponent": fixture["opponent"],
                "baseline": baseline,
                "candidate": candidate,
                "reward_delta": candidate["reward"] - baseline["reward"],
                "margin_delta": candidate["margin"] - baseline["margin"],
            }
        )

    rescue = next(row for row in rows if row["episode_id"] == 93891282)
    assert rescue["candidate"]["early_animal_loss"]["COW"] <= 2, rescue
    assert (
        rescue["candidate"]["early_animal_loss"]["COW"]
        < rescue["baseline"]["early_animal_loss"]["COW"]
    ), rescue
    assert rescue["candidate"]["reward"] > rescue["baseline"]["reward"], rescue
    assert sum(row["reward_delta"] for row in rows) > 0, rows
    return {
        "ok": True,
        "fixtures": len(rows),
        "total_reward_delta": sum(row["reward_delta"] for row in rows),
        "total_margin_delta": sum(row["margin_delta"] for row in rows),
        "rows": rows,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
