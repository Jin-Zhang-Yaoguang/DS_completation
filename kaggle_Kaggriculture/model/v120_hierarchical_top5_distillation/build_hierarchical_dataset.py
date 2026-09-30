#!/usr/bin/env python3
"""把 Public Replay 压缩成 72-turn、24-turn 与全局三层 option 数据。"""

from __future__ import annotations

from collections import Counter
from datetime import date
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
RECEIPT = HERE / "replay_data/download_receipt.json"
OUT = HERE / "dataset"
MANIFEST = HERE / "dataset_manifest.json"
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
SHOPS = ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "ICE_CREAM_SHOP", "FARMERS_MARKET", "YARN_STORE", "PET_CAFE", "JUICE_BAR")
MOVE_OPS = {"NORTH", "SOUTH", "EAST", "WEST"}
TASK_OPS = ("PLANT", "WATER", "HARVEST", "FERTILIZE", "BUILD_COOP", "BUILD_PASTURE", "FEED", "CARE", "COLLECT_FERTILIZER", "PICKUP", "PLACE", "DROP", "DIG")


def number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def tile_counts(farm: dict) -> Counter:
    counts: Counter = Counter()
    for row in farm.get("tiles", []) or []:
        for tile in row if isinstance(row, list) else ():
            if not isinstance(tile, dict):
                continue
            if tile.get("crop"):
                counts[f"crop_{tile['crop']}"] += 1
            if tile.get("animal"):
                counts[f"animal_{tile['animal']}"] += 1
            if tile.get("kind"):
                counts[f"kind_{tile['kind']}"] += 1
    return counts


def state_features(obs: dict, previous_obs: dict | None = None) -> dict[str, float]:
    seat = int(obs["player"])
    farms = obs["farms"]
    own, opponent = farms[seat], farms[1 - seat]
    private = obs.get("private", {}) or {}
    features: dict[str, float] = {
        "day": number(obs.get("day")),
        "season_fraction": number(obs.get("day")) / 30.0,
        "own_money": number(own.get("money")),
        "opponent_money": number(opponent.get("money")),
        "money_gap": number(own.get("money")) - number(opponent.get("money")),
        "own_hands": number(len(own.get("hands", []) or [])),
        "opponent_hands": number(len(opponent.get("hands", []) or [])),
        "own_quadrants": number(len(own.get("unlocked_quadrants", []) or [])),
        "opponent_quadrants": number(len(opponent.get("unlocked_quadrants", []) or [])),
    }
    shops = Counter(str(value) for value in (obs.get("town", {}).get("unlocked_shops", []) or []))
    for shop in SHOPS:
        features[f"shop_{shop}"] = number(shops.get(shop, 0))
    own_tiles, opponent_tiles = tile_counts(own), tile_counts(opponent)
    for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"):
        features[f"own_crop_{item}"] = number(own_tiles.get(f"crop_{item}", 0))
        features[f"opponent_crop_{item}"] = number(opponent_tiles.get(f"crop_{item}", 0))
    for item in ("COW", "SHEEP", "GOOSE"):
        features[f"own_animal_{item}"] = number(own_tiles.get(f"animal_{item}", 0))
        features[f"opponent_animal_{item}"] = number(opponent_tiles.get(f"animal_{item}", 0))
    shed = private.get("shed", {}) or {}
    seeds = private.get("seeds", {}) or {}
    for item in PRODUCTS:
        features[f"shed_{item}"] = number(shed.get(item, 0))
        features[f"price_{item}"] = number(obs.get("market", {}).get("prices", {}).get(item, 0))
        inventory = number(obs.get("market", {}).get("inventory", {}).get(item, 0))
        features[f"market_{item}"] = inventory
        old = inventory
        if previous_obs is not None:
            old = number(previous_obs.get("market", {}).get("inventory", {}).get(item, inventory))
        features[f"market_delta_{item}"] = inventory - old
    for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"):
        features[f"seed_{item}"] = number(seeds.get(item, 0))
    return features


def distance_to_shed(position: list | tuple) -> int:
    x, y = int(position[0]), int(position[1])
    return min(abs(x - sx) + abs(y - sy) for sx, sy in ((4, 4), (5, 4), (4, 5), (5, 5)))


def action_for(replay: dict, turn: int, seat: int) -> dict:
    # Kaggle Replay 的 action 存在执行后的下一状态，必须右移一格对齐 observation。
    return replay["steps"][turn + 1][seat].get("action") or {"farmer": ["PASS"], "hands": [], "market": []}


def window_stats(replay: dict, seat: int, start: int, stop: int) -> dict[str, float]:
    stats: Counter = Counter()
    task_distances: list[int] = []
    for turn in range(start, min(stop, 719)):
        obs = replay["steps"][turn][seat]["observation"]
        action = action_for(replay, turn, seat)
        farm = obs["farms"][seat]
        positions = [farm.get("farmer", [4, 4]), *(farm.get("hands", []) or [])]
        unit_actions = [action.get("farmer", ["PASS"]), *(action.get("hands", []) or [])]
        for index, order in enumerate(unit_actions):
            op = str((order or ["PASS"])[0])
            stats[f"op_{op}"] += 1
            if op in MOVE_OPS:
                stats["moves"] += 1
            elif op != "PASS":
                stats["productive_actions"] += 1
                if index < len(positions):
                    task_distances.append(distance_to_shed(positions[index]))
        for order in action.get("market", []) or []:
            if not order:
                continue
            op = str(order[0])
            quantity = number(order[2]) if len(order) >= 3 else 1.0
            stats[f"market_{op}"] += quantity
            if op in {"SELL", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"} and len(order) >= 2:
                stats[f"{op}_{order[1]}"] += quantity
            if op == "SELL" and turn % 4 in (1, 2, 3) and len(order) >= 2:
                stats[f"EARLY_SELL_{order[1]}"] += quantity
    stats["mean_task_distance"] = sum(task_distances) / len(task_distances) if task_distances else 0.0
    stats["productive_per_move"] = stats["productive_actions"] / max(1.0, stats["moves"])
    return {key: float(value) for key, value in stats.items()}


def option_label(stats: dict[str, float], day: int, layer: str) -> str:
    if day >= 27 and stats.get("market_SELL", 0) >= stats.get("market_BUY_SEED", 0):
        return "LIQUIDATE"
    animal = stats.get("op_BUILD_PASTURE", 0) + stats.get("op_BUILD_COOP", 0) + stats.get("market_BUY_ANIMAL", 0)
    crop = stats.get("op_PLANT", 0) + stats.get("market_BUY_SEED", 0)
    labor = stats.get("market_HIRE", 0) + stats.get("market_BUY_LAND", 0)
    logistics = stats.get("op_PICKUP", 0) + stats.get("op_PLACE", 0) + stats.get("op_DROP", 0)
    scores = {"ANIMAL_SCALE": animal, "CROP_SCALE": crop, "LABOR_SCALE": labor, "LOGISTICS": logistics}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ("DAILY_MAINTENANCE" if layer == "day" else "HOLD")


def teacher_rows(replay: dict, source: dict, teacher: dict) -> tuple[list[dict], list[dict], list[dict]]:
    episode_id, seat = int(source["episode_id"]), int(teacher["seat"])
    base = {"episode_id": episode_id, "replay_sha256": source["sha256"], "actual_date": source["actual_date"], "teacher": teacher["team"], "submission_id": teacher["submission_id"], "seat": seat}
    shop_rows, day_rows, global_rows = [], [], []
    previous_cycle: dict[str, float] = {}
    for day in range(0, 30, 3):
        turn = day * 24
        obs = replay["steps"][turn][seat]["observation"]
        previous_obs = replay["steps"][max(0, turn - 72)][seat]["observation"] if turn else None
        target = window_stats(replay, seat, turn, turn + 72)
        delta = {f"delta_{key}": value - previous_cycle.get(key, 0.0) for key, value in target.items()}
        shop_rows.append({**base, "decision_day": day, "features": state_features(obs, previous_obs), "target": {**target, **delta}, "option": option_label(target, day, "shop")})
        previous_cycle = target
    for day in range(30):
        turn = day * 24
        obs = replay["steps"][turn][seat]["observation"]
        previous_obs = replay["steps"][max(0, turn - 24)][seat]["observation"] if turn else None
        target = window_stats(replay, seat, turn, turn + 24)
        day_rows.append({**base, "decision_day": day, "shop_cycle_day": day - day % 3, "features": state_features(obs, previous_obs), "target": target, "option": option_label(target, day, "day")})
        opponent_target = window_stats(replay, 1 - seat, turn, turn + 24)
        global_target = {}
        for item in PRODUCTS:
            global_target[f"own_early_sell_{item}"] = target.get(f"EARLY_SELL_{item}", 0.0)
            global_target[f"opponent_next_sell_{item}"] = opponent_target.get(f"SELL_{item}", 0.0)
        global_rows.append({**base, "decision_day": day, "features": state_features(obs, previous_obs), "target": global_target})
    return shop_rows, day_rows, global_rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    minimum = date.fromisoformat("2026-08-20")
    OUT.mkdir(parents=True, exist_ok=True)
    shop_rows: list[dict] = []
    day_rows: list[dict] = []
    global_rows: list[dict] = []
    for source in receipt["rows"]:
        if date.fromisoformat(source["actual_date"]) < minimum:
            raise ValueError(f"过期 Replay: {source['episode_id']}")
        if str(source["module_version"]) != "1.32.7":
            raise ValueError(f"规则版本不一致: {source['episode_id']} {source['module_version']}")
        replay = json.loads(Path(source["path"]).read_text(encoding="utf-8"))
        for teacher in source["teachers"]:
            a, b, c = teacher_rows(replay, source, teacher)
            shop_rows.extend(a); day_rows.extend(b); global_rows.extend(c)
    write_jsonl(OUT / "shop_refresh.jsonl", shop_rows)
    write_jsonl(OUT / "daily_movement.jsonl", day_rows)
    write_jsonl(OUT / "global_strategy.jsonl", global_rows)
    episode_ids = sorted({row["episode_id"] for row in day_rows})
    manifest = {
        "schema": "kaggriculture-v120-hierarchical-dataset-v1",
        "alignment": "steps[t].observation -> steps[t+1].action",
        "split_unit": "episode_id",
        "episodes": len(episode_ids),
        "teacher_trajectories": len(day_rows) // 30,
        "rows": {"shop_refresh": len(shop_rows), "daily_movement": len(day_rows), "global_strategy": len(global_rows)},
        "teachers": dict(Counter(row["teacher"] for row in shop_rows)),
        "episode_ids": episode_ids,
        "status": "PILOT_NOT_PROMOTABLE",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
