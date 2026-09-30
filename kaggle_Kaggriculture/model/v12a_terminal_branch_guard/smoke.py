"""Small paired closed-loop screen for V12A versus its exact r002 parent."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from kaggle_environments import make

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    create_agent as create_registered_agent,
    load_registry,
)
from kaggle_Kaggriculture.model.v12a_terminal_branch_guard.main import make_agent


HERE = Path(__file__).resolve().parent
V11 = HERE.parent / "v11_iterative_league"
REGISTRY_PATH = V11 / "runs" / "round_002" / "strategy" / "registry_next.json"
PANEL_PATH = V11 / "runs" / "round_003" / "panel.json"
REPORT_PATH = HERE / "smoke_report.json"


class Capture:
    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.final_obs: Any = None

    def __call__(self, obs: Any, configuration: Any = None):
        self.final_obs = obs
        return self.agent(obs, configuration)


def _unsold(obs: Any) -> int:
    private = getattr(obs, "private", None)
    if private is None and isinstance(obs, dict):
        private = obs.get("private", {})
    shed = getattr(private, "shed", None)
    if shed is None and isinstance(private, dict):
        shed = private.get("shed", {})
    return sum(max(0, int(value or 0)) for value in dict(shed or {}).values())


def run(seed_count: int = 4) -> dict[str, Any]:
    registry = load_registry(REGISTRY_PATH)
    panel = json.loads(PANEL_PATH.read_text(encoding="utf-8"))["records"][: int(seed_count)]
    games: list[dict[str, Any]] = []
    branch_counts: Counter[str] = Counter()
    for source in panel:
        for candidate_seat in (0, 1):
            candidate = make_agent()
            parent = create_registered_agent(
                registry, "r002_learned_router_topday_animal_throttle"
            )
            candidate_capture = Capture(candidate)
            parent_capture = Capture(parent)
            agents = [candidate_capture, parent_capture]
            if candidate_seat == 1:
                agents.reverse()
            env = make(
                "kaggriculture",
                configuration={"seed": int(source["seed"])},
                debug=True,
            )
            steps = env.run(agents)
            final = steps[-1]
            rewards = [float(state.reward or 0.0) for state in final]
            statuses = [str(state.status) for state in final]
            candidate_reward = rewards[candidate_seat]
            parent_reward = rewards[1 - candidate_seat]
            diagnostics = candidate.diagnostics()
            branch = str((diagnostics.get("parent_diagnostics") or {}).get("selected"))
            branch_counts[branch] += 1
            games.append(
                {
                    "date": source["date"],
                    "episode_id": source["episode_id"],
                    "seed": int(source["seed"]),
                    "candidate_seat": candidate_seat,
                    "steps": len(steps),
                    "statuses": statuses,
                    "candidate_reward": candidate_reward,
                    "parent_reward": parent_reward,
                    "candidate_margin": candidate_reward - parent_reward,
                    "score": 1.0 if candidate_reward > parent_reward else 0.5 if candidate_reward == parent_reward else 0.0,
                    "candidate_terminal_shed": _unsold(candidate_capture.final_obs),
                    "parent_terminal_shed": _unsold(parent_capture.final_obs),
                    "selected_branch": branch,
                    "changed_steps": diagnostics["changed_steps"],
                    "throttle_steps": diagnostics["throttle_steps"],
                    "terminal_fill_steps": diagnostics["terminal_fill_steps"],
                    "residual_fallbacks": diagnostics["residual_fallbacks"],
                }
            )
    all_done = all(
        row["steps"] == 720 and row["statuses"] == ["DONE", "DONE"]
        for row in games
    )
    result = {
        "schema": "kaggriculture-v12a-small-paired-smoke-1",
        "scope": "development smoke only; not a formal acceptance result",
        "parent": "r002_learned_router_topday_animal_throttle",
        "seeds": len(panel),
        "games": len(games),
        "all_done": all_done,
        "zero_residual_fallbacks": all(row["residual_fallbacks"] == 0 for row in games),
        "score_rate": sum(row["score"] for row in games) / len(games),
        "wins": sum(row["score"] == 1.0 for row in games),
        "draws": sum(row["score"] == 0.5 for row in games),
        "losses": sum(row["score"] == 0.0 for row in games),
        "mean_gold_margin": sum(row["candidate_margin"] for row in games) / len(games),
        "terminal_shed_total": {
            "candidate": sum(row["candidate_terminal_shed"] for row in games),
            "parent": sum(row["parent_terminal_shed"] for row in games),
        },
        "selected_branches": dict(branch_counts),
        "changed_games": sum(row["changed_steps"] > 0 for row in games),
        "games_detail": games,
    }
    REPORT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not all_done or not result["zero_residual_fallbacks"]:
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    run()

