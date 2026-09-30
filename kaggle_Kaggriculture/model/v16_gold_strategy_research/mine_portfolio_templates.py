#!/usr/bin/env python3
"""Mine state-conditional production portfolios from recent public Replays.

The output is descriptive rather than causal.  It is used to discover complete
production templates and routing features for the next closed-loop search.
Only the newest N episodes per named team are fully parsed; all files are first
indexed from their small JSON header.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"
DEFAULT_TEAMS = ("Crop Dusta", "Ryo Hasegawa", "Subramanya N", "tetsuya", "Kronki", "tyz123456")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def header(path: Path) -> dict | None:
    text = path.open(errors="ignore").read(6000)
    episode = re.search(r'"EpisodeId":\s*(\d+)', text)
    teams = re.search(r'"TeamNames":\s*(\[[^\]]*\])', text)
    rewards = re.search(r'"rewards":\s*(\[[^\]]*\])', text)
    if not (episode and teams and rewards):
        return None
    return {
        "episode_id": int(episode.group(1)),
        "teams": json.loads(teams.group(1)),
        "rewards": json.loads(rewards.group(1)),
        "path": path,
    }


def observation_at(replay: dict, seat: int, index: int) -> dict:
    steps = replay.get("steps") or []
    if not steps:
        return {}
    row = steps[min(max(0, index), len(steps) - 1)][seat]
    return row.get("observation") or {}


def count_public_tiles(farm: dict) -> dict[str, int]:
    result: Counter[str] = Counter()
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if not isinstance(tile, dict):
                continue
            for key in ("crop", "animal", "kind"):
                value = str(tile.get(key, ""))
                if value:
                    result[value] += 1
                    break
    return dict(result)


def parse_perspective(replay: dict, team: str) -> dict:
    teams = replay["info"]["TeamNames"]
    seat = teams.index(team)
    seed_buys: Counter[str] = Counter()
    animal_buys: Counter[str] = Counter()
    plants: Counter[str] = Counter()
    sells: Counter[str] = Counter()
    market_orders: Counter[str] = Counter()
    land_requests = []
    hire_requests = []
    for step, pair in enumerate((replay.get("steps") or [])[1:720]):
        action = pair[seat].get("action") or {}
        for order in [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]:
            if len(order) >= 2 and order[0] == "PLANT":
                plants[str(order[1])] += 1
        for order in action.get("market", []) or []:
            if not order:
                continue
            op = str(order[0])
            market_orders[op] += 1
            if op == "BUY_SEED" and len(order) >= 3:
                seed_buys[str(order[1])] += max(0, int(order[2] or 0))
            elif op == "BUY_ANIMAL" and len(order) >= 3:
                animal_buys[str(order[1])] += max(0, int(order[2] or 0))
            elif op == "SELL" and len(order) >= 3:
                sells[str(order[1])] += max(0, int(order[2] or 0))
            elif op == "BUY_LAND":
                land_requests.append(step)
            elif op == "HIRE":
                hire_requests.append(step)

    checkpoint = observation_at(replay, seat, 169)
    final = observation_at(replay, seat, 719)
    early_shops = tuple((checkpoint.get("town") or {}).get("unlocked_shops", []) or [])
    own_farm = ((checkpoint.get("farms") or [{}, {}])[seat])
    opponent_farm = ((checkpoint.get("farms") or [{}, {}])[1 - seat])
    land3_observed = None
    max_hands = 0
    for index, pair in enumerate(replay.get("steps") or []):
        obs = pair[seat].get("observation") or {}
        farms = obs.get("farms") or []
        if seat >= len(farms):
            continue
        farm = farms[seat]
        max_hands = max(max_hands, len(farm.get("hands", []) or []))
        if land3_observed is None and len(farm.get("unlocked_quadrants", []) or []) >= 3:
            land3_observed = index

    return {
        "episode_id": int(replay["info"]["EpisodeId"]),
        "seed": int(replay["info"]["seed"]),
        "team": team,
        "seat": seat,
        "opponent": teams[1 - seat],
        "reward": float(replay.get("rewards", [0, 0])[seat]),
        "early_shops": list(early_shops),
        "seed_buys": {item: int(seed_buys[item]) for item in CROPS},
        "animal_buys": {item: int(animal_buys[item]) for item in ANIMALS},
        "plant_requests": {item: int(plants[item]) for item in CROPS},
        "sell_requests": {item: int(sells[item]) for item in PRODUCTS},
        "land3_observed_step": land3_observed,
        "max_hands": max_hands,
        "early_own_tiles": count_public_tiles(own_farm),
        "early_opponent_tiles": count_public_tiles(opponent_farm),
        "final_shops": list((final.get("town") or {}).get("unlocked_shops", []) or []),
        "final_money_observed": float((((final.get("farms") or [{}, {}])[seat]).get("money", 0) or 0)),
    }


def vector_median(rows: list[dict], key: str, labels: tuple[str, ...]) -> dict[str, float]:
    return {
        label: statistics.median(float(row[key].get(label, 0)) for row in rows)
        for label in labels
    }


def summarize_team(rows: list[dict]) -> dict:
    portfolios = Counter(
        tuple(row["seed_buys"].get(item, 0) for item in CROPS)
        + tuple(row["animal_buys"].get(item, 0) for item in ANIMALS)
        for row in rows
    )
    by_shops: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in rows:
        by_shops[tuple(row["early_shops"])].append(row)
    return {
        "episodes": len(rows),
        "reward_median": statistics.median(row["reward"] for row in rows),
        "unique_portfolios": len(portfolios),
        "most_common_portfolios": [
            {"vector": list(vector), "count": count} for vector, count in portfolios.most_common(5)
        ],
        "overall_seed_median": vector_median(rows, "seed_buys", CROPS),
        "overall_animal_median": vector_median(rows, "animal_buys", ANIMALS),
        "land3_step_median": statistics.median(
            row["land3_observed_step"] for row in rows if row["land3_observed_step"] is not None
        ),
        "max_hands_median": statistics.median(row["max_hands"] for row in rows),
        "shop_conditioned": [
            {
                "shops": list(shops),
                "n": len(group),
                "reward_median": statistics.median(row["reward"] for row in group),
                "seed_median": vector_median(group, "seed_buys", CROPS),
                "animal_median": vector_median(group, "animal_buys", ANIMALS),
            }
            for shops, group in sorted(by_shops.items(), key=lambda item: (-len(item[1]), item[0]))
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest-per-team", type=int, default=12)
    parser.add_argument("--teams", default=",".join(DEFAULT_TEAMS))
    parser.add_argument("--include-rows", action="store_true")
    args = parser.parse_args()
    teams = tuple(value.strip() for value in args.teams.split(",") if value.strip())
    selected: dict[str, list[dict]] = {team: [] for team in teams}
    for path in DATA.glob("*.json"):
        row = header(path)
        if row is None:
            continue
        for team in set(row["teams"]) & set(teams):
            selected[team].append(row)
    for team in teams:
        selected[team] = sorted(selected[team], key=lambda row: row["episode_id"], reverse=True)[: args.latest_per_team]

    cache = {}
    rows = []
    for team in teams:
        for indexed in selected[team]:
            path = indexed["path"]
            if path not in cache:
                cache[path] = json.loads(path.read_text())
            rows.append(parse_perspective(cache[path], team))
    result = {
        "status": "DESCRIPTIVE_TEMPLATE_MINING_NOT_CAUSAL",
        "source_date": "2026-08-25",
        "latest_per_team": args.latest_per_team,
        "teams": {team: summarize_team([row for row in rows if row["team"] == team]) for team in teams if any(row["team"] == team for row in rows)},
    }
    if args.include_rows:
        result["rows"] = rows
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
