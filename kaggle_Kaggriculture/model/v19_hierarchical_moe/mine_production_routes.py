#!/usr/bin/env python3
"""Mine exact-prefix-compatible production routes from local public replays."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
DEFAULT_DATA = PROJECT / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"
DEFAULT_PREFIX_REPLAY = DEFAULT_DATA / "99609968.json"
TEAMS = ("tyz123456", "Kronki")
PREFIX_EPISODE = 99609968
PREFIX_TEAM = "tyz123456"
ROUTER_STEP = 72


def digest(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def actions_for(replay: dict, team: str) -> tuple[int, list[dict]]:
    seat = replay["info"]["TeamNames"].index(team)
    actions = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
    return seat, actions


def production_signature(actions: list[dict]) -> list[dict]:
    """Keep geometry/labour/unit work and fixed production purchases, omit sells."""
    result = []
    for action in actions:
        market = []
        for raw in action.get("market") or []:
            order = list(raw)
            if order and order[0] in {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT"}:
                market.append(order)
        result.append({
            "farmer": list(action.get("farmer") or ["PASS"]),
            "hands": [list(order or ["PASS"]) for order in (action.get("hands") or [])],
            "market": market,
        })
    return result


def shops_at(replay: dict, seat: int, step: int) -> list[str]:
    cell = replay["steps"][step][seat]
    observation = cell.get("observation") or {}
    return [str(value) for value in ((observation.get("town") or {}).get("unlocked_shops") or [])]


def terminal_reward(replay: dict, seat: int) -> tuple[float, float]:
    own = replay["steps"][-1][seat].get("reward")
    opp = replay["steps"][-1][1 - seat].get("reward")
    return float(own or 0), float(opp or 0)


def purchase_totals(actions: list[dict]) -> dict:
    result = {"seed": Counter(), "animal": Counter(), "hires": 0, "land": 0}
    for action in actions:
        for order in action.get("market") or []:
            if not order:
                continue
            if order[0] == "BUY_SEED" and len(order) >= 3:
                result["seed"][str(order[1])] += max(0, int(order[2] or 0))
            elif order[0] == "BUY_ANIMAL" and len(order) >= 3:
                result["animal"][str(order[1])] += max(0, int(order[2] or 0))
            elif order[0] == "HIRE":
                result["hires"] += 1
            elif order[0] == "BUY_LAND":
                result["land"] += 1
    return {
        "seed": dict(result["seed"]), "animal": dict(result["animal"]),
        "hires": int(result["hires"]), "land": int(result["land"]),
    }


def candidate_paths(data: Path) -> list[Path]:
    result = []
    for path in data.glob("*.json"):
        with path.open(errors="ignore") as handle:
            head = handle.read(6000)
        if any(team in head for team in TEAMS):
            result.append(path)
    return sorted(result, key=lambda path: int(path.stem))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--prefix-replay", type=Path, default=DEFAULT_PREFIX_REPLAY)
    parser.add_argument("--output", type=Path, default=HERE / "production_route_catalog.json")
    args = parser.parse_args()

    prefix_replay = json.loads(args.prefix_replay.read_text(encoding="utf-8"))
    _, prefix_actions = actions_for(prefix_replay, PREFIX_TEAM)
    canonical_prefix_hash = digest(prefix_actions[:ROUTER_STEP])

    rows = []
    parsed = set()
    for path in candidate_paths(args.data):
        replay = json.loads(path.read_text(encoding="utf-8"))
        episode = int(replay["info"]["EpisodeId"])
        for team in TEAMS:
            if team not in replay["info"]["TeamNames"]:
                continue
            key = (episode, team)
            if key in parsed:
                continue
            parsed.add(key)
            seat, actions = actions_for(replay, team)
            own, opp = terminal_reward(replay, seat)
            prefix_hash = digest(actions[:ROUTER_STEP])
            rows.append({
                "episode": episode,
                "team": team,
                "seat": seat,
                "path": str(path.resolve()),
                "source_seed": int(replay["info"].get("seed") or 0),
                "source_reward": own,
                "source_opponent_reward": opp,
                "source_margin": own - opp,
                "source_result": "W" if own > opp else "T" if own == opp else "L",
                "shops_step72": shops_at(replay, seat, 72),
                "shops_step144": shops_at(replay, seat, 144),
                "shops_step216": shops_at(replay, seat, 216),
                "prefix_hash": prefix_hash,
                "exact_parent_prefix": prefix_hash == canonical_prefix_hash,
                "full_action_hash": digest(actions),
                "production_hash": digest(production_signature(actions)),
                "purchases": purchase_totals(actions),
            })

    compatible = [row for row in rows if row["exact_parent_prefix"]]
    by_production = defaultdict(list)
    for row in compatible:
        by_production[row["production_hash"]].append(row)
    representatives = []
    for production_hash, group in by_production.items():
        best = max(group, key=lambda row: (row["source_result"] == "W", row["source_margin"], row["source_reward"], row["episode"]))
        representatives.append({
            **best,
            "production_hash": production_hash,
            "group_games": len(group),
            "group_episodes": sorted({int(row["episode"]) for row in group}),
            "group_teams": sorted({str(row["team"]) for row in group}),
            "group_first_shops": dict(Counter((row["shops_step72"] or ["NO_SHOP"])[0] for row in group)),
        })
    representatives.sort(key=lambda row: (row["source_result"] == "W", row["source_margin"], row["source_reward"]), reverse=True)

    result = {
        "schema": "kaggriculture-v19-production-route-catalog-v1",
        "data": str(args.data.resolve()),
        "teams": list(TEAMS),
        "router_step": ROUTER_STEP,
        "canonical_prefix_episode": PREFIX_EPISODE,
        "canonical_prefix_team": PREFIX_TEAM,
        "canonical_prefix_replay": str(args.prefix_replay.resolve()),
        "canonical_prefix_hash": canonical_prefix_hash,
        "parsed_team_episode_rows": len(rows),
        "exact_prefix_rows": len(compatible),
        "unique_exact_prefix_full_actions": len({row["full_action_hash"] for row in compatible}),
        "unique_exact_prefix_production_signatures": len(by_production),
        "representatives": representatives,
        "rows": rows,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "data", "teams", "canonical_prefix_hash", "parsed_team_episode_rows",
        "exact_prefix_rows", "unique_exact_prefix_full_actions",
        "unique_exact_prefix_production_signatures",
    )}, ensure_ascii=False, indent=2))
    for row in representatives[:20]:
        print(json.dumps({key: row[key] for key in (
            "team", "episode", "source_reward", "source_margin", "shops_step72",
            "shops_step144", "shops_step216", "group_games", "purchases",
        )}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
