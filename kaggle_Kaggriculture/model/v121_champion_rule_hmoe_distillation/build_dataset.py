#!/usr/bin/env python3
"""把 Top5 Replay 转成无 tape 的三层合同蒸馏数据。"""

from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "v120_hierarchical_top5_distillation"
RECEIPT = SOURCE / "replay_data/download_receipt.json"
OUT = HERE / "dataset"
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
SHOPS = ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "ICE_CREAM_SHOP", "FARMERS_MARKET", "YARN_STORE", "PET_CAFE", "JUICE_BAR", "SMOOTHIE_SHOP")
MOVE = {"NORTH", "SOUTH", "EAST", "WEST"}


def number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def private_hash(obs: dict) -> str:
    """只用于数据对齐审计；哈希不进入训练特征。"""
    payload = json.dumps(obs.get("private", {}) or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def tile_summary(farm: dict) -> tuple[Counter, list[tuple[int, int, dict]]]:
    counts: Counter = Counter()
    cells: list[tuple[int, int, dict]] = []
    for y, row in enumerate(farm.get("tiles", []) or []):
        for x, tile in enumerate(row if isinstance(row, list) else []):
            if not isinstance(tile, dict):
                continue
            cells.append((x, y, tile))
            crop = tile.get("crop")
            animal = tile.get("animal")
            if isinstance(animal, dict):
                animal = animal.get("kind")
            kind = tile.get("kind")
            if crop:
                counts[f"crop_{crop}"] += 1
            if animal:
                counts[f"animal_{animal}"] += 1
            if kind:
                counts[f"kind_{kind}"] += 1
    return counts, cells


def center_distance(position: list | tuple) -> int:
    x, y = int(position[0]), int(position[1])
    return min(abs(x - sx) + abs(y - sy) for sx, sy in ((4, 4), (5, 4), (4, 5), (5, 5)))


def state_features(obs: dict, previous: dict | None = None) -> dict[str, float]:
    seat = int(obs.get("player", 0) or 0)
    farms = list(obs.get("farms", []) or [{}, {}])
    while len(farms) < 2:
        farms.append({})
    own, rival = farms[seat], farms[1 - seat]
    own_counts, _ = tile_summary(own)
    rival_counts, _ = tile_summary(rival)
    private = obs.get("private", {}) or {}
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    features: dict[str, float] = {
        "day": float(day),
        "hour": float(hour),
        "season_fraction": day / 30.0,
        "own_money": number(own.get("money")),
        "rival_money": number(rival.get("money")),
        "money_gap": number(own.get("money")) - number(rival.get("money")),
        "own_hands": float(len(own.get("hands", []) or [])),
        "rival_hands": float(len(rival.get("hands", []) or [])),
        "own_lands": float(len(own.get("unlocked_quadrants", []) or [])),
        "rival_lands": float(len(rival.get("unlocked_quadrants", []) or [])),
        "shed_used": float(sum(max(0, int(v or 0)) for v in (private.get("shed", {}) or {}).values())),
    }
    shops = Counter(str(value) for value in (obs.get("town", {}).get("unlocked_shops", []) or []))
    for shop in SHOPS:
        features[f"shop_{shop}"] = float(shops.get(shop, 0))
    for crop in CROPS:
        features[f"own_crop_{crop}"] = float(own_counts.get(f"crop_{crop}", 0))
        features[f"rival_crop_{crop}"] = float(rival_counts.get(f"crop_{crop}", 0))
        features[f"seed_{crop}"] = number((private.get("seeds", {}) or {}).get(crop))
    for animal in ANIMALS:
        features[f"own_animal_{animal}"] = float(own_counts.get(f"animal_{animal}", 0))
        features[f"rival_animal_{animal}"] = float(rival_counts.get(f"animal_{animal}", 0))
    market = obs.get("market", {}) or {}
    old_market = (previous or {}).get("market", {}) or {}
    for item in PRODUCTS:
        inventory = number((market.get("inventory", {}) or {}).get(item))
        old_inventory = number((old_market.get("inventory", {}) or {}).get(item, inventory))
        price = number((market.get("prices", {}) or {}).get(item))
        old_price = number((old_market.get("prices", {}) or {}).get(item, price))
        features[f"shed_{item}"] = number((private.get("shed", {}) or {}).get(item))
        features[f"market_{item}"] = inventory
        features[f"market_delta_{item}"] = inventory - old_inventory
        features[f"price_{item}"] = price
        features[f"price_delta_{item}"] = price - old_price
    return features


def action_at(replay: dict, turn: int, seat: int) -> dict:
    return replay["steps"][turn + 1][seat].get("action") or {"farmer": ["PASS"], "hands": [], "market": []}


def window_targets(replay: dict, seat: int, start: int, stop: int) -> dict[str, float]:
    result: Counter = Counter()
    task_distance: list[int] = []
    center_animal: list[int] = []
    top_row_plants: list[int] = []
    for turn in range(start, min(stop, 719)):
        obs = replay["steps"][turn][seat]["observation"]
        farm = obs["farms"][seat]
        positions = [farm.get("farmer", [4, 4]), *(farm.get("hands", []) or [])]
        action = action_at(replay, turn, seat)
        units = [action.get("farmer", ["PASS"]), *(action.get("hands", []) or [])]
        for actor, raw in enumerate(units):
            order = list(raw or ["PASS"])
            op = str(order[0])
            result[f"unit_{op}"] += 1
            if op in MOVE:
                result["moves"] += 1
                continue
            if op == "PASS":
                result["idle"] += 1
                continue
            result["productive"] += 1
            if actor < len(positions):
                pos = positions[actor]
                distance = center_distance(pos)
                task_distance.append(distance)
                result["center_tasks"] += float(distance <= 2)
                if op in {"BUILD_PASTURE", "BUILD_COOP", "PLACE"}:
                    center_animal.append(int(distance <= 2))
                if op == "PLANT":
                    top_row_plants.append(int(int(pos[1]) % 5 <= 1))
        for raw in action.get("market", []) or []:
            order = list(raw or [])
            if not order:
                continue
            op = str(order[0])
            quantity = number(order[2]) if len(order) >= 3 else 1.0
            result[f"market_{op}"] += quantity
            if len(order) >= 2:
                result[f"market_{op}_{order[1]}"] += quantity
            if op == "SELL" and turn % 4 != 0 and len(order) >= 2:
                result[f"early_sell_{order[1]}"] += quantity
    result["mean_task_distance"] = sum(task_distance) / len(task_distance) if task_distance else 0.0
    result["productive_per_move"] = result["productive"] / max(1.0, result["moves"])
    result["center_task_share"] = result["center_tasks"] / max(1.0, result["productive"])
    result["center_livestock_share"] = sum(center_animal) / len(center_animal) if center_animal else 0.0
    result["top_two_row_plant_share"] = sum(top_row_plants) / len(top_row_plants) if top_row_plants else 0.0
    return {str(key): float(value) for key, value in result.items()}


def expert_label(target: dict[str, float], day: int) -> str:
    if day >= 27:
        return "LIQUIDATE"
    # 用近似资本/长期价值加权，避免大量低价值 PLANT 次数淹没畜牧信号。
    scores = {
        "LIVESTOCK": 450 * target.get("market_BUY_ANIMAL", 0) + 300 * (
            target.get("unit_BUILD_PASTURE", 0) + target.get("unit_BUILD_COOP", 0)
        ) + 40 * (target.get("unit_FEED", 0) + target.get("unit_CARE", 0)),
        "CROP": 40 * target.get("market_BUY_SEED", 0) + 35 * target.get("unit_PLANT", 0)
        + 15 * target.get("unit_WATER", 0) + 20 * target.get("unit_FERTILIZE", 0),
        "CAPACITY": 700 * target.get("market_BUY_LAND", 0) + 120 * target.get("market_HIRE", 0),
        "LOGISTICS": 25 * (target.get("unit_PICKUP", 0) + target.get("unit_PLACE", 0) + target.get("unit_DROP", 0))
        + 5 * target.get("moves", 0),
    }
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "MAINTENANCE"


def build_rows(replay: dict, source: dict, teacher: dict) -> tuple[list[dict], list[dict], list[dict]]:
    episode = int(source["episode_id"])
    seat = int(teacher["seat"])
    base = {
        "episode_id": episode,
        "replay_sha256": source["sha256"],
        "actual_date": source["actual_date"],
        "teacher": teacher["team"],
        "submission_id": int(teacher["submission_id"]),
        "seat": seat,
    }
    macro: list[dict] = []
    daily: list[dict] = []
    global_rows: list[dict] = []
    for day in range(0, 30, 3):
        turn = day * 24
        obs = replay["steps"][turn][seat]["observation"]
        previous = replay["steps"][max(0, turn - 72)][seat]["observation"] if turn else None
        target = window_targets(replay, seat, turn, turn + 72)
        macro.append({**base, "decision_day": day, "features": state_features(obs, previous), "target": target, "expert": expert_label(target, day)})
    for day in range(30):
        turn = day * 24
        obs = replay["steps"][turn][seat]["observation"]
        previous = replay["steps"][max(0, turn - 24)][seat]["observation"] if turn else None
        target = window_targets(replay, seat, turn, turn + 24)
        daily.append({**base, "decision_day": day, "cycle_day": day - day % 3, "features": state_features(obs, previous), "target": target, "expert": expert_label(target, day)})
        rival = window_targets(replay, 1 - seat, turn, turn + 24)
        global_target = {}
        for item in PRODUCTS:
            global_target[f"own_early_sell_{item}"] = target.get(f"early_sell_{item}", 0.0)
            global_target[f"rival_next_sell_{item}"] = rival.get(f"market_SELL_{item}", 0.0)
        global_rows.append({**base, "decision_day": day, "features": state_features(obs, previous), "target": global_target})
    return macro, daily, global_rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    seen: set[tuple[int, str]] = set()
    macro: list[dict] = []
    daily: list[dict] = []
    global_rows: list[dict] = []
    for source in receipt["rows"]:
        identity = (int(source["episode_id"]), str(source["sha256"]))
        if identity in seen:
            raise ValueError(f"重复 Replay: {identity}")
        seen.add(identity)
        if date.fromisoformat(source["actual_date"]) < date(2026, 8, 20):
            raise ValueError(f"过期 Replay: {identity}")
        if str(source.get("module_version")) != "1.32.7":
            raise ValueError(f"规则版本不一致: {identity}")
        path = Path(source["path"])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"Replay SHA 不匹配: {identity}")
        replay = json.loads(raw)
        for teacher in source["teachers"]:
            a, b, c = build_rows(replay, source, teacher)
            macro.extend(a); daily.extend(b); global_rows.extend(c)
    OUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT / "macro_3day.jsonl", macro)
    write_jsonl(OUT / "daily_contract.jsonl", daily)
    write_jsonl(OUT / "global_market.jsonl", global_rows)
    manifest = {
        "schema": "kaggriculture-v121-contract-distillation-dataset-v1",
        "source": "current Top5 public Replay teacher trajectories",
        "admission": {"minimum_actual_date": "2026-08-20", "engine": "1.32.7", "dedupe": "episode_id + replay_sha256"},
        "alignment": "steps[t].observation -> aggregate steps[t+1:t+h].actions",
        "split_unit": "episode_id",
        "episodes": len(seen),
        "teacher_trajectories": len(daily) // 30,
        "teachers": dict(Counter(row["teacher"] for row in daily)),
        "rows": {"macro_3day": len(macro), "daily_contract": len(daily), "global_market": len(global_rows)},
        "expert_distribution": {"macro": dict(Counter(row["expert"] for row in macro)), "daily": dict(Counter(row["expert"] for row in daily))},
        "forbidden_runtime_fields": ["episode_id", "replay_sha256", "teacher", "submission_id", "seat", "seed", "future_shop"],
        "status": "RESEARCH_DATA_ONLY",
    }
    (HERE / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
