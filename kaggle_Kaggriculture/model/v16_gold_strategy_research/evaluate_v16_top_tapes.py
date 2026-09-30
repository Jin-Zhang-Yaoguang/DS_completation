#!/usr/bin/env python3
"""Paired V16-vs-parent stress test against recent top-team fixed tapes.

Fixed tapes are not closed-loop opponents, so this is a deployment stress test,
not a gold-competitiveness estimate.  The paired delta does reveal whether the
V16 overlay is fragile under recent strong market flows.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from mine_portfolio_templates import DATA, DEFAULT_TEAMS, header


ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
A2 = MODEL / "v1_adaptive_market" / "main.py"
V16 = MODEL / "v16_s2_town_drain_challenger" / "main.py"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"


def load_cppsim():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError("cppsim is not built")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = load_cppsim()


def load_agent(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def play(seed: int, own_seat: int, own_agent, fixed: list[list[dict]]) -> tuple[float, float]:
    game = KAGSIM.Game(seed)
    while not game.done:
        step = game.step_count
        actions = [fixed[0][step], fixed[1][step]]
        actions[own_seat] = own_agent(game.observe(own_seat))
        game.step(actions[0], actions[1])
    return float(game.reward(0)), float(game.reward(1))


def summarize(rows: list[dict]) -> dict:
    own = [row["own_delta"] for row in rows]
    margin = [row["margin_delta"] for row in rows]
    return {
        "comparisons": len(rows),
        "own_positive_zero_negative": [sum(x > 0 for x in own), sum(x == 0 for x in own), sum(x < 0 for x in own)],
        "own_delta_mean": statistics.mean(own),
        "own_delta_median": statistics.median(own),
        "margin_positive_zero_negative": [sum(x > 0 for x in margin), sum(x == 0 for x in margin), sum(x < 0 for x in margin)],
        "margin_delta_mean": statistics.mean(margin),
        "margin_delta_median": statistics.median(margin),
        "baseline_wins": sum(row["baseline_own"] > row["baseline_opp"] for row in rows),
        "candidate_wins": sum(row["candidate_own"] > row["candidate_opp"] for row in rows),
        "win_to_loss": sum(row["baseline_own"] > row["baseline_opp"] and row["candidate_own"] <= row["candidate_opp"] for row in rows),
        "loss_to_win": sum(row["baseline_own"] <= row["baseline_opp"] and row["candidate_own"] > row["candidate_opp"] for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest-per-team", type=int, default=12)
    parser.add_argument("--teams", default=",".join(DEFAULT_TEAMS))
    parser.add_argument("--output", default=str(Path(__file__).with_name("v16_top_tape_stress.json")))
    args = parser.parse_args()
    teams = tuple(value.strip() for value in args.teams.split(",") if value.strip())
    selected = {team: [] for team in teams}
    for path in DATA.glob("*.json"):
        indexed = header(path)
        if indexed is None:
            continue
        for team in set(indexed["teams"]) & set(teams):
            selected[team].append(indexed)
    for team in teams:
        selected[team] = sorted(selected[team], key=lambda row: row["episode_id"], reverse=True)[:args.latest_per_team]

    parent = load_agent(A2, "v16_stress_parent")
    candidate = load_agent(V16, "v16_stress_candidate")
    rows = []
    for team in teams:
        for indexed in selected[team]:
            replay = json.loads(indexed["path"].read_text())
            top_seat = replay["info"]["TeamNames"].index(team)
            own_seat = 1 - top_seat
            fixed = [[pair[seat].get("action") or {} for pair in replay["steps"][1:720]] for seat in (0, 1)]
            seed = int(replay["info"]["seed"])
            baseline = play(seed, own_seat, parent, fixed)
            trial = play(seed, own_seat, candidate, fixed)
            rows.append({
                "episode_id": int(replay["info"]["EpisodeId"]), "team": team, "own_seat": own_seat,
                "baseline_own": baseline[own_seat], "baseline_opp": baseline[top_seat],
                "candidate_own": trial[own_seat], "candidate_opp": trial[top_seat],
                "own_delta": trial[own_seat] - baseline[own_seat],
                "margin_delta": (trial[own_seat] - trial[top_seat]) - (baseline[own_seat] - baseline[top_seat]),
            })
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["team"]].append(row)
    result = {
        "status": "FIXED_TOP_TAPE_STRESS_NOT_CLOSED_LOOP_GOLD_EVIDENCE",
        "engine": KAGSIM.ENGINE_VERSION,
        "source_date": "2026-08-25",
        "overall": summarize(rows),
        "by_team": {team: summarize(grouped[team]) for team in teams if grouped[team]},
        "rows": rows,
    }
    output = Path(args.output)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "engine", "overall", "by_team")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
