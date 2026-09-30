#!/usr/bin/env python3
"""从 Top20 训练轨迹提取日级空间占用先验，不保留动作序列。"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median

from build_contract_dataset import load_sources


HERE = Path(__file__).resolve().parent


def main() -> int:
    sources, _ = load_sources()
    sources = [source for source in sources if source["split"] == "train"]
    grouped: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for source in sources:
        grouped[(int(source["episode_id"]), str(source["sha256"]))].append(source)
    cell_animals = {day: defaultdict(Counter) for day in range(30)}
    cell_crops = {day: defaultdict(Counter) for day in range(30)}
    totals = {day: {"animals": [], "crops": [], "lands": []} for day in range(30)}
    teachers = Counter()
    for index, group in enumerate(grouped.values(), 1):
        replay = json.loads(Path(group[0]["path"]).read_bytes())
        for source in group:
            teacher = source["teachers"][0]
            seat = int(teacher["seat"]); teachers[str(teacher["team"])] += 1
            for day in range(30):
                obs = replay["steps"][day * 24][seat]["observation"]
                farm = obs["farms"][seat]
                animal_total = crop_total = 0
                for y, row in enumerate(farm.get("tiles", []) or []):
                    for x, tile in enumerate(row):
                        if not isinstance(tile, dict):
                            continue
                        animal, crop = tile.get("animal"), tile.get("crop")
                        if animal:
                            cell_animals[day][(x, y)][str(animal)] += 1; animal_total += 1
                        if crop:
                            cell_crops[day][(x, y)][str(crop)] += 1; crop_total += 1
                totals[day]["animals"].append(animal_total)
                totals[day]["crops"].append(crop_total)
                totals[day]["lands"].append(len(farm.get("unlocked_quadrants", []) or []))
        if index % 30 == 0 or index == len(grouped):
            print(f"processed {index}/{len(grouped)} replays", flush=True)
    days = {}
    for day in range(30):
        animal_score = {f"{x},{y}": sum(counter.values()) / len(totals[day]["animals"]) for (x, y), counter in cell_animals[day].items()}
        animal_rank = sorted(animal_score, key=lambda key: (-animal_score[key], sum(abs(int(v)-4) for v in key.split(',')), key))
        crop_map = {}
        crop_score = {}
        for (x, y), counter in cell_crops[day].items():
            crop, count = counter.most_common(1)[0]
            crop_map[f"{x},{y}"] = crop
            crop_score[f"{x},{y}"] = count / len(totals[day]["crops"])
        days[str(day)] = {
            "target_animals": int(round(median(totals[day]["animals"]))),
            "target_crops": int(round(median(totals[day]["crops"]))),
            "target_lands": int(round(median(totals[day]["lands"]))),
            "animal_rank": animal_rank, "animal_score": animal_score,
            "crop_map": crop_map, "crop_score": crop_score,
        }
    payload = {
        "schema": "kaggriculture-v122-top20-spatial-priors-v1", "source": "train-only Top20 teacher observations at day boundaries",
        "contains_action_sequence": False, "episodes": len(grouped), "teacher_trajectories": sum(teachers.values()),
        "teachers": dict(teachers), "days": days, "status": "TRAINING_AUXILIARY_NOT_PROMOTION_EVIDENCE",
    }
    (HERE / "spatial_priors.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in payload.items() if k != "days"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
