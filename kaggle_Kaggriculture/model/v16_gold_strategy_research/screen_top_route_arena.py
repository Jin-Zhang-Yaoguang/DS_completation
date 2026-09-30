#!/usr/bin/env python3
"""Broad fixed-stream arena for recent top-team production routes.

This arena is a hypothesis generator: replay streams are fixed, not live
policies.  Cross-seed and two-seat play measures schedule robustness and market
interaction without treating any one incumbent as the optimization target.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from mine_portfolio_templates import DATA, DEFAULT_TEAMS, header


ROOT = Path(__file__).resolve().parents[3]
CPPSIM = ROOT / "kaggle_Kaggriculture" / "model" / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"


def load_cppsim():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError("cppsim is not built")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = load_cppsim()


def route_id(team: str, episode: int) -> str:
    return f"{team}::{episode}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--routes-per-team", type=int, default=3)
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--teams", default=",".join(DEFAULT_TEAMS))
    parser.add_argument("--output", default=str(Path(__file__).with_name("top_route_arena.json")))
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
        selected[team] = sorted(selected[team], key=lambda row: row["episode_id"], reverse=True)[:args.routes_per_team]

    routes = []
    for team in teams:
        for indexed in selected[team]:
            replay = json.loads(indexed["path"].read_text())
            seat = replay["info"]["TeamNames"].index(team)
            actions = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
            rid = route_id(team, int(replay["info"]["EpisodeId"]))
            routes.append({"id": rid, "team": team, "episode_id": int(replay["info"]["EpisodeId"]),
                           "source_seed": int(replay["info"]["seed"]), "stream": KAGSIM.Stream(actions)})

    jobs, labels = [], []
    for left, right in combinations(routes, 2):
        if left["team"] == right["team"]:
            continue
        for seed in range(args.seeds):
            jobs.append((left["stream"], right["stream"], seed))
            labels.append((left["id"], right["id"], seed, 0))
            jobs.append((right["stream"], left["stream"], seed))
            labels.append((left["id"], right["id"], seed, 1))
    rewards = KAGSIM.run_many(jobs)
    route_rows = defaultdict(list)
    pair_rows = defaultdict(list)
    for label, reward in zip(labels, rewards, strict=True):
        left, right, seed, swapped = label
        if swapped:
            left_reward, right_reward = float(reward[1]), float(reward[0])
        else:
            left_reward, right_reward = float(reward[0]), float(reward[1])
        pair_rows[(left, right)].append((left_reward, right_reward))
        route_rows[left].append((left_reward, right_reward))
        route_rows[right].append((right_reward, left_reward))

    def stats(rows):
        scores = [1.0 if own > opp else 0.5 if own == opp else 0.0 for own, opp in rows]
        margins = [own - opp for own, opp in rows]
        return {"games": len(rows), "score_rate": statistics.mean(scores), "win_rate": statistics.mean(own > opp for own, opp in rows),
                "mean_bank": statistics.mean(own for own, _ in rows), "mean_margin": statistics.mean(margins),
                "margin_p10": sorted(margins)[max(0, int(0.10 * len(margins)) - 1)]}

    route_meta = {row["id"]: row for row in routes}
    by_route = {rid: {**stats(rows), "team": route_meta[rid]["team"], "episode_id": route_meta[rid]["episode_id"],
                       "source_seed": route_meta[rid]["source_seed"]} for rid, rows in route_rows.items()}
    team_rows = defaultdict(list)
    for rid, rows in route_rows.items():
        team_rows[route_meta[rid]["team"]].extend(rows)
    result = {
        "status": "FIXED_STREAM_META_PROXY_NOT_LIVE_POLICY_EVIDENCE",
        "engine": KAGSIM.ENGINE_VERSION,
        "source_date": "2026-08-25",
        "routes_per_team": args.routes_per_team,
        "seeds": args.seeds,
        "episodes": len(jobs),
        "by_team": {team: stats(team_rows[team]) for team in teams if team_rows[team]},
        "by_route": dict(sorted(by_route.items(), key=lambda item: item[1]["score_rate"], reverse=True)),
        "pair_score_rate": {f"{left}__vs__{right}": stats(rows) for (left, right), rows in pair_rows.items()},
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "engine", "episodes", "by_team", "by_route")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
