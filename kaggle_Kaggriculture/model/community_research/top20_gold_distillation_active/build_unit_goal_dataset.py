#!/usr/bin/env python3
"""将 Top20 连续移动压缩为单位级最终任务标签。"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import random

import numpy as np

from build_contract_dataset import load_sources
from contract_features import action_at
from goal_features import goal_label, unit_context, unit_features


HERE = Path(__file__).resolve().parent
OUT = HERE / "unit_goal_data"
MOVE = {"NORTH", "SOUTH", "EAST", "WEST"}


def unit_orders(replay: dict, turn: int, seat: int) -> list[list]:
    action = action_at(replay, turn, seat)
    return [list(action.get("farmer") or ["PASS"]), *[list(v or ["PASS"]) for v in (action.get("hands") or [])]]


def positions(replay: dict, turn: int, seat: int) -> list[tuple[int, int]]:
    obs = replay["steps"][turn][seat]["observation"]
    farm = obs["farms"][seat]
    return [tuple(map(int, farm.get("farmer") or [4, 4])), *[tuple(map(int, p)) for p in (farm.get("hands") or [])]]


def target_order(replay: dict, turn: int, seat: int, actor: int) -> tuple[list, int]:
    current = unit_orders(replay, turn, seat)
    if actor >= len(current):
        return ["PASS"], turn
    order = current[actor]
    if order and order[0] not in MOVE:
        return order, turn
    day_end = min(718, (turn // 24 + 1) * 24 - 1)
    for future in range(turn + 1, min(day_end, turn + 12) + 1):
        orders = unit_orders(replay, future, seat)
        if actor >= len(orders):
            break
        candidate = orders[actor]
        if candidate and candidate[0] not in MOVE and candidate[0] != "PASS":
            return candidate, future
    return ["PASS"], turn


class Reservoir:
    def __init__(self, limit: int, seed: int):
        self.limit = limit; self.rng = random.Random(seed); self.seen = Counter(); self.rows = defaultdict(list)

    def add(self, label: str, vector: list[float], meta: tuple[int, ...]) -> None:
        self.seen[label] += 1
        bucket = self.rows[label]
        row = (np.asarray(vector, dtype=np.float32), meta)
        if len(bucket) < self.limit:
            bucket.append(row); return
        index = self.rng.randrange(self.seen[label])
        if index < self.limit:
            bucket[index] = row

    def arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        labels = sorted(self.rows)
        data = [(vector, label, meta) for label in labels for vector, meta in self.rows[label]]
        self.rng.shuffle(data)
        return (np.stack([v for v, _, _ in data]), np.asarray([label for _, label, _ in data]),
                np.asarray([meta for _, _, meta in data], dtype=np.int64))


def main() -> int:
    sources, _ = load_sources()
    by_replay = defaultdict(list)
    for source in sources:
        by_replay[(int(source["episode_id"]), str(source["sha256"]))].append(source)
    reservoirs = {"train": Reservoir(24000, 1221), "dev": Reservoir(8000, 1222)}
    names = None; trajectories = Counter()
    for index, group in enumerate(by_replay.values(), 1):
        replay = json.loads(Path(group[0]["path"]).read_bytes())
        for source in group:
            teacher = source["teachers"][0]; seat = int(teacher["seat"]); split = str(source["split"])
            trajectories[split] += 1
            previous_day = None
            for turn in range(719):
                obs = replay["steps"][turn][seat]["observation"]
                if turn % 24 == 0:
                    previous_day = replay["steps"][max(0, turn-24)][seat]["observation"] if turn else None
                context = unit_context(obs, previous_day)
                current_positions = positions(replay, turn, seat)
                for actor in range(len(current_positions)):
                    order, target_turn = target_order(replay, turn, seat, actor)
                    target_positions = positions(replay, target_turn, seat)
                    target_position = target_positions[actor] if actor < len(target_positions) else current_positions[actor]
                    target_obs = replay["steps"][target_turn][seat]["observation"]
                    target_tile = target_obs["farms"][seat]["tiles"][target_position[1]][target_position[0]]
                    label = goal_label(order, target_tile)
                    features = unit_features(obs, actor, previous_day, context)
                    if names is None:
                        names = sorted(features)
                    reservoirs[split].add(label, [float(features.get(name, 0.0)) for name in names],
                                          (int(source["episode_id"]), seat, turn, actor, int(target_position[0]), int(target_position[1])))
        if index % 20 == 0 or index == len(by_replay):
            print(f"processed {index}/{len(by_replay)} replays", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    counts = {}
    for split, reservoir in reservoirs.items():
        x, y, meta = reservoir.arrays()
        np.savez_compressed(OUT / f"{split}.npz", x=x, y=y, meta=meta)
        counts[split] = {"sampled": len(y), "seen": dict(reservoir.seen), "saved": dict(Counter(y.tolist()))}
    manifest = {
        "schema": "kaggriculture-top20-unit-goal-dataset-v1", "idea": "movement suffix -> eventual semantic task",
        "lookahead_max": 12, "crosses_day_boundary": False, "feature_names": names,
        "episodes": len(by_replay), "teacher_trajectories": dict(trajectories), "counts": counts,
        "split_unit": "episode_id", "status": "IDEA_DEVELOPMENT_DATA_NOT_MODEL_VERSION",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in manifest.items() if k not in {"feature_names", "counts"}}, ensure_ascii=False, indent=2))
    print(json.dumps({split: {"sampled": value["sampled"], "classes": len(value["saved"])} for split, value in counts.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
