#!/usr/bin/env python3
"""Fast fixed-stream screen for exact-prefix production-route candidates."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
DATA = PROJECT / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
import kagsim  # type: ignore


ROUTER_STEP = 72
OPPONENTS = (
    ("Crop Dusta", 99625995),
    ("Ryo Hasegawa", 99625995),
    ("Subramanya N", 99607808),
    ("tetsuya", 99612231),
    ("Kronki", 99628290),
    ("tyz123456", 99630579),
)
KNOWN_ROUTES = {
    ("tyz123456", 99609968),
    ("tyz123456", 99616937),
    ("Kronki", 99596430),
}


def route(team: str, episode: int, path: Path | None = None) -> list[dict]:
    replay = json.loads((path or DATA / f"{episode}.json").read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(team)
    return [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]


def profile_key(row: dict) -> tuple:
    purchases = row["purchases"]
    return (
        tuple(sorted(purchases["seed"].items())),
        tuple(sorted(purchases["animal"].items())),
        int(purchases["hires"]), int(purchases["land"]),
    )


def select_candidates(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[profile_key(row)].append(row)
    selected = {}
    for profile_index, (_, group) in enumerate(sorted(groups.items(), key=lambda item: len(item[1]), reverse=True), start=1):
        by_shop = defaultdict(list)
        for row in group:
            by_shop[(row["shops_step72"] or ["NO_SHOP"])[0]].append(row)
        picks = [max(values, key=lambda row: (row["source_result"] == "W", row["source_margin"], row["source_reward"])) for values in by_shop.values()]
        picks += [
            max(group, key=lambda row: row["source_reward"]),
            max(group, key=lambda row: row["episode"]),
        ]
        picks += [row for row in group if (row["team"], int(row["episode"])) in KNOWN_ROUTES]
        for row in picks:
            key = row["full_action_hash"]
            selected[key] = {**row, "profile": f"P{profile_index}"}
    return sorted(selected.values(), key=lambda row: (row["profile"], row["team"], row["episode"]))


def shop_label(prefix: list[dict], opponent: list[dict], seed: int, seat: int) -> str:
    game = kagsim.Game(seed)
    while game.step_count < ROUTER_STEP:
        step = game.step_count
        pair = [None, None]
        pair[seat] = prefix[step]
        pair[1 - seat] = opponent[step]
        game.step(pair[0], pair[1])
    shops = list(game.observe(seat)["town"]["unlocked_shops"])
    return shops[0] if shops else "NO_SHOP"


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def summarize(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "score_rate": statistics.mean(score(row["margin"]) for row in rows),
        "mean_bank": statistics.mean(row["own"] for row in rows),
        "mean_margin": statistics.mean(row["margin"] for row in rows),
    }


def family_equal(rows: list[dict]) -> dict:
    families = sorted({row["opponent_team"] for row in rows})
    by_family = {family: summarize([row for row in rows if row["opponent_team"] == family]) for family in families}
    return {
        **summarize(rows),
        "family_equal_score_rate": statistics.mean(value["score_rate"] for value in by_family.values()),
        "worst_family_score_rate": min(value["score_rate"] for value in by_family.values()),
        "by_family": by_family,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev-seeds", type=int, default=32)
    parser.add_argument("--test-seeds", type=int, default=32)
    parser.add_argument("--dev-start", type=int, default=60000)
    parser.add_argument("--test-start", type=int, default=61000)
    parser.add_argument("--output", type=Path, default=HERE / "production_route_l0_screen.json")
    args = parser.parse_args()

    catalog = json.loads((HERE / "production_route_catalog.json").read_text(encoding="utf-8"))
    candidates = select_candidates([row for row in catalog["rows"] if row["exact_parent_prefix"]])
    streams = {
        row["full_action_hash"]: route(row["team"], int(row["episode"]), Path(row["path"]))
        for row in candidates
    }
    opponents = {
        f"{team}::{episode}": {"team": team, "episode": episode, "actions": route(team, episode)}
        for team, episode in OPPONENTS
    }
    prefix = route("tyz123456", 99609968)
    splits = {
        "dev": range(args.dev_start, args.dev_start + args.dev_seeds),
        "test": range(args.test_start, args.test_start + args.test_seeds),
    }
    rows_by_split = {name: [] for name in splits}
    for split, seeds in splits.items():
        for opponent_id, opponent in opponents.items():
            jobs, labels = [], []
            for seed in seeds:
                for seat in (0, 1):
                    shop = shop_label(prefix, opponent["actions"], seed, seat)
                    for candidate in candidates:
                        actions = streams[candidate["full_action_hash"]]
                        hybrid = prefix[:ROUTER_STEP] + actions[ROUTER_STEP:]
                        pair = (kagsim.Stream(hybrid), kagsim.Stream(opponent["actions"])) if seat == 0 else (kagsim.Stream(opponent["actions"]), kagsim.Stream(hybrid))
                        jobs.append((*pair, seed))
                        labels.append((candidate, opponent_id, opponent["team"], seed, seat, shop))
            rewards = kagsim.run_many(jobs)
            for (candidate, opponent_id, opponent_team, seed, seat, shop), reward in zip(labels, rewards, strict=True):
                own, opp = float(reward[seat]), float(reward[1 - seat])
                rows_by_split[split].append({
                    "route_hash": candidate["full_action_hash"],
                    "route_id": f'{candidate["team"]}::{candidate["episode"]}',
                    "profile": candidate["profile"], "source_first_shop": (candidate["shops_step72"] or ["NO_SHOP"])[0],
                    "opponent": opponent_id, "opponent_team": opponent_team,
                    "seed": seed, "seat": seat, "shop": shop,
                    "own": own, "opp": opp, "margin": own - opp,
                })

    dev, test = rows_by_split["dev"], rows_by_split["test"]
    route_dev = {
        candidate["full_action_hash"]: family_equal([row for row in dev if row["route_hash"] == candidate["full_action_hash"]])
        for candidate in candidates
    }
    choices = {}
    for shop in sorted({row["shop"] for row in dev}):
        metrics = {}
        for candidate in candidates:
            selected = [row for row in dev if row["shop"] == shop and row["route_hash"] == candidate["full_action_hash"]]
            if selected:
                metrics[candidate["full_action_hash"]] = family_equal(selected)
        choices[shop] = max(metrics, key=lambda key: (
            metrics[key]["family_equal_score_rate"], metrics[key]["worst_family_score_rate"], metrics[key]["mean_margin"],
        ))

    routed_test = [row for row in test if row["route_hash"] == choices[row["shop"]]]
    best_single = max(route_dev, key=lambda key: (
        route_dev[key]["family_equal_score_rate"], route_dev[key]["worst_family_score_rate"], route_dev[key]["mean_margin"],
    ))
    metadata = {row["full_action_hash"]: row for row in candidates}
    result = {
        "schema": "kaggriculture-v19-production-route-l0-screen-v1",
        "status": "FIXED_STREAM_SCREEN_NOT_LIVE_POLICY_EVIDENCE",
        "engine": str(kagsim.ENGINE_VERSION),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "split": {
            "dev": [args.dev_start, args.dev_start + args.dev_seeds - 1],
            "test": [args.test_start, args.test_start + args.test_seeds - 1],
        },
        "best_single": {"route": metadata[best_single], "dev": route_dev[best_single], "test": family_equal([row for row in test if row["route_hash"] == best_single])},
        "shop_choices": {shop: metadata[key] for shop, key in choices.items()},
        "shop_router_test": family_equal(routed_test),
        "route_dev": route_dev,
        "rows": rows_by_split,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate_count": len(candidates),
        "best_single": {"id": f'{metadata[best_single]["team"]}::{metadata[best_single]["episode"]}', "profile": metadata[best_single]["profile"], **route_dev[best_single]},
        "shop_choices": {shop: f'{metadata[key]["team"]}::{metadata[key]["episode"]} ({metadata[key]["profile"]})' for shop, key in choices.items()},
        "shop_router_test": result["shop_router_test"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
