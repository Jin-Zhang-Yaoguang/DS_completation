#!/usr/bin/env python3
"""Train/evaluate a public-shop router over complete recent top route tails.

The town shop is public and causal.  A route is selected once, at day 3, and
the selected route's whole remaining production schedule is kept intact.
This first-stage screen intentionally uses fixed replay streams; it is an
offline upper-bound / route-selection experiment, not live-policy evidence.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
DATA = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
TEAMS = ("Crop Dusta", "Ryo Hasegawa", "Subramanya N", "tetsuya", "Kronki", "tyz123456")
ROUTER_STEP = 72


def load_cppsim():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError("cppsim build missing")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = load_cppsim()


def header(path: Path) -> dict | None:
    # Full parsing is acceptable for the small newest-date slice selected here.
    try:
        replay = json.loads(path.read_text())
    except Exception:
        return None
    info = replay.get("info") or {}
    names = info.get("TeamNames") or []
    if len(names) != 2:
        return None
    return {"path": path, "episode": int(info["EpisodeId"]), "teams": names, "replay": replay}


def newest_routes(per_team: int) -> list[dict]:
    selected: dict[str, list[dict]] = {team: [] for team in TEAMS}
    for path in DATA.glob("*.json"):
        # Avoid loading every large replay: the episode id is the filename and
        # team names occur near the start.
        text = path.open(errors="ignore").read(5000)
        for team in TEAMS:
            if json.dumps(team) in text:
                selected[team].append({"path": path, "episode": int(path.stem)})
    rows = []
    for team in TEAMS:
        for item in sorted(selected[team], key=lambda row: row["episode"], reverse=True)[:per_team]:
            replay = json.loads(item["path"].read_text())
            seat = replay["info"]["TeamNames"].index(team)
            actions = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
            rows.append({
                "id": f"{team}::{item['episode']}", "team": team,
                "episode": item["episode"], "seat": seat, "actions": actions,
            })
    return rows


def shop_label(prefix: list[dict], opponent: list[dict], seed: int, seat: int) -> str:
    game = KAGSIM.Game(seed)
    while game.step_count < ROUTER_STEP:
        step = game.step_count
        pair = [None, None]
        pair[seat] = prefix[step]
        pair[1 - seat] = opponent[step]
        game.step(pair[0], pair[1])
    shops = list(game.observe(seat)["town"]["unlocked_shops"])
    return shops[0] if shops else "NO_SHOP"


def score(own: float, opp: float) -> float:
    return 1.0 if own > opp else 0.5 if own == opp else 0.0


def metric(rows: list[dict]) -> dict:
    margins = sorted(row["own"] - row["opp"] for row in rows)
    tail_n = max(1, int(len(margins) * 0.10))
    return {
        "games": len(rows),
        "score_rate": statistics.mean(score(row["own"], row["opp"]) for row in rows),
        "mean_bank": statistics.mean(row["own"] for row in rows),
        "mean_margin": statistics.mean(margins),
        "margin_p10": margins[max(0, tail_n - 1)],
        "margin_cvar10": statistics.mean(margins[:tail_n]),
    }


def family_equal(rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["opponent_team"]].append(row)
    family = {name: metric(group) for name, group in groups.items()}
    return {
        "family_equal_score_rate": statistics.mean(value["score_rate"] for value in family.values()),
        "worst_family_score_rate": min(value["score_rate"] for value in family.values()),
        "by_family": family,
        **metric(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--routes-per-team", type=int, default=3)
    parser.add_argument("--dev-seeds", type=int, default=160)
    parser.add_argument("--test-seeds", type=int, default=160)
    parser.add_argument("--test-start", type=int, default=10000)
    parser.add_argument("--output", default=str(HERE / "route_shop_oracle_results.json"))
    args = parser.parse_args()

    routes = newest_routes(args.routes_per_team)
    by_team: dict[str, list[dict]] = defaultdict(list)
    for route in routes:
        by_team[route["team"]].append(route)
    # The two selected continuations have exactly the same first 72 actions.
    # Using that native prefix makes the switch resource/position compatible by
    # construction, rather than relying on rejected orders to hide mismatch.
    prefix_route = next(row for row in routes if row["id"] == "tyz123456::99609968")
    opponents = [max(rows, key=lambda row: row["episode"]) for rows in by_team.values()]

    splits = {
        "dev": range(args.dev_seeds),
        "test": range(args.test_start, args.test_start + args.test_seeds),
    }
    all_rows: dict[str, list[dict]] = {name: [] for name in splits}
    for split, seeds in splits.items():
        jobs, labels = [], []
        for opponent in opponents:
            for seed in seeds:
                for seat in (0, 1):
                    shop = shop_label(prefix_route["actions"], opponent["actions"], seed, seat)
                    for route in routes:
                        hybrid = prefix_route["actions"][:ROUTER_STEP] + route["actions"][ROUTER_STEP:]
                        if seat == 0:
                            jobs.append((KAGSIM.Stream(hybrid), KAGSIM.Stream(opponent["actions"]), seed))
                        else:
                            jobs.append((KAGSIM.Stream(opponent["actions"]), KAGSIM.Stream(hybrid), seed))
                        labels.append((route, opponent, seed, seat, shop))
        rewards = KAGSIM.run_many(jobs)
        for (route, opponent, seed, seat, shop), reward in zip(labels, rewards, strict=True):
            all_rows[split].append({
                "route": route["id"], "route_team": route["team"],
                "opponent": opponent["id"], "opponent_team": opponent["team"],
                "seed": seed, "seat": seat, "shop": shop,
                "own": float(reward[seat]), "opp": float(reward[1 - seat]),
            })

    dev = all_rows["dev"]
    test = all_rows["test"]
    # Route choice is trained solely on development seeds.  Use family-equal
    # score, then worst-family score, then mean margin to avoid high-volume bias.
    choices = {}
    for shop in sorted({row["shop"] for row in dev}):
        candidates = {}
        for route in routes:
            subset = [row for row in dev if row["shop"] == shop and row["route"] == route["id"]]
            if subset:
                candidates[route["id"]] = family_equal(subset)
        choices[shop] = max(
            candidates,
            key=lambda rid: (
                candidates[rid]["family_equal_score_rate"],
                candidates[rid]["worst_family_score_rate"],
                candidates[rid]["mean_margin"],
            ),
        )

    def routed_rows(source: list[dict]) -> list[dict]:
        return [row for row in source if row["route"] == choices[row["shop"]]]

    single_dev = {route["id"]: family_equal([row for row in dev if row["route"] == route["id"]]) for route in routes}
    best_single = max(single_dev, key=lambda rid: (single_dev[rid]["family_equal_score_rate"], single_dev[rid]["worst_family_score_rate"]))
    best_single_test = family_equal([row for row in test if row["route"] == best_single])
    router_test = family_equal(routed_rows(test))

    # Hindsight per-game oracle is deliberately labelled unattainable: it is
    # useful only to determine whether route diversity contains material upside.
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in test:
        grouped[(row["opponent"], row["seed"], row["seat"])].append(row)
    oracle = [max(group, key=lambda row: (score(row["own"], row["opp"]), row["own"] - row["opp"])) for group in grouped.values()]

    result = {
        "status": "FIXED_STREAM_ROUTE_SELECTION_SCREEN_NOT_LIVE_POLICY_EVIDENCE",
        "engine": KAGSIM.ENGINE_VERSION,
        "source_date": "2026-08-25",
        "router_step": ROUTER_STEP,
        "common_prefix": prefix_route["id"],
        "routes": [{key: row[key] for key in ("id", "team", "episode")} for row in routes],
        "opponent_routes": [{key: row[key] for key in ("id", "team", "episode")} for row in opponents],
        "split": {"dev": [0, args.dev_seeds - 1], "test": [args.test_start, args.test_start + args.test_seeds - 1]},
        "shop_route_choices": choices,
        "best_single_route": best_single,
        "best_single_test": best_single_test,
        "shop_router_test": router_test,
        "unattainable_per_game_oracle_test": family_equal(oracle),
        "route_dev": single_dev,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "choices": choices, "best_single": best_single,
        "best_single_test": best_single_test, "shop_router_test": router_test,
        "oracle_test": result["unattainable_per_game_oracle_test"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
