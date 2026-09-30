"""Build stride-1 high-score Replay data with inferred role and route-target options."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np

import action_space as space
import build_offline_dataset
import features


MOVE_TOKENS = {space.UNIT_INDEX[name] for name in space.MOVES}
PASS_TOKEN = space.UNIT_INDEX["PASS"]
STAGE_NAMES = (
    "IDLE", "BUILD", "PICKUP", "PLACE", "PLANT", "MAINTAIN",
    "HARVEST", "DROP", "DIG", "MOVE_ONLY",
)


def token_stage(token: int) -> int:
    name = space.UNIT_TOKENS[int(token)]
    op = name.split(":", 1)[0]
    return {
        "PASS": 0, "BUILD_COOP": 1, "BUILD_PASTURE": 1,
        "PICKUP": 2, "PLACE": 3, "PLANT": 4,
        "WATER": 5, "FERTILIZE": 5, "FEED": 5, "CARE": 5,
        "COLLECT_FERTILIZER": 5, "HARVEST": 6, "DROP": 7, "DIG": 8,
    }.get(op, 9)


def infer_options(arrays: dict[str, np.ndarray], horizon: int = 24):
    roles = np.zeros((len(arrays["step"]), features.MAX_UNITS), dtype=np.int16)
    stages = np.zeros((len(arrays["step"]), features.MAX_UNITS), dtype=np.int16)
    targets = np.full((len(arrays["step"]), features.MAX_UNITS), 44, dtype=np.int16)
    groups: dict[tuple[int, int], list[int]] = {}
    for index, key in enumerate(zip(arrays["episode"], arrays["seat"])):
        groups.setdefault((int(key[0]), int(key[1])), []).append(index)
    for indices in groups.values():
        indices.sort(key=lambda index: int(arrays["step"][index]))
        for offset, index in enumerate(indices):
            step = int(arrays["step"][index])
            for unit_index in range(features.MAX_UNITS):
                if not arrays["unit_mask"][index, unit_index]:
                    continue
                x = int(round(float(arrays["units"][index, unit_index, 2]) * 9.0))
                y = int(round(float(arrays["units"][index, unit_index, 3]) * 9.0))
                token = int(arrays["unit_tokens"][index, unit_index])
                targets[index, unit_index] = y * features.BOARD_SIZE + x
                if token == PASS_TOKEN:
                    continue
                roles[index, unit_index] = 1
                stages[index, unit_index] = token_stage(token)
                if token not in MOVE_TOKENS:
                    continue
                route_target = (x, y)
                for future_offset in range(offset + 1, min(len(indices), offset + horizon + 1)):
                    future = indices[future_offset]
                    if int(arrays["step"][future]) // 24 != step // 24:
                        break
                    if not arrays["unit_mask"][future, unit_index]:
                        break
                    future_x = int(round(float(arrays["units"][future, unit_index, 2]) * 9.0))
                    future_y = int(round(float(arrays["units"][future, unit_index, 3]) * 9.0))
                    route_target = (future_x, future_y)
                    future_token = int(arrays["unit_tokens"][future, unit_index])
                    if future_token not in MOVE_TOKENS and future_token != PASS_TOKEN:
                        stages[index, unit_index] = token_stage(future_token)
                        break
                    if future_token == PASS_TOKEN:
                        break
                targets[index, unit_index] = route_target[1] * features.BOARD_SIZE + route_target[0]
    return roles, stages, targets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--team", help="Keep only the named team's seat from every replay.")
    args = parser.parse_args()
    arrays, metadata = build_offline_dataset.build(args.replay, stride=1)
    rewards = []
    selected_seats = {}
    for path in args.replay:
        replay = json.loads(path.read_text(encoding="utf-8"))
        replay_rewards = [float(value or 0.0) for value in (replay.get("rewards") or [])[:2]]
        if args.team:
            teams = list((replay.get("info") or {}).get("TeamNames") or [])
            if args.team not in teams:
                raise ValueError(f"team {args.team!r} is absent from {path}")
            seat = teams.index(args.team)
            selected_seats[int(path.stem)] = seat
            rewards.append(replay_rewards[seat])
        else:
            rewards.extend(replay_rewards)
    if args.team:
        keep = np.asarray([
            selected_seats.get(int(episode), -1) == int(seat)
            for episode, seat in zip(arrays["episode"], arrays["seat"])
        ])
        arrays = {key: value[keep] for key, value in arrays.items()}
        metadata["rows"] = int(np.sum(keep))
        metadata["selected_team"] = args.team
    arrays["option_roles"], arrays["option_stages"], arrays["option_targets"] = infer_options(
        arrays, args.horizon
    )
    metadata.update({
        "schema": "kaggriculture-v113-replay-role-option-v1",
        "route_target_horizon": args.horizon,
        "option_active_rows": int(np.sum(arrays["option_roles"])),
        "option_stage_contract": {str(index): name for index, name in enumerate(STAGE_NAMES)},
        "option_stage_rows": {
            str(index): int(np.sum(arrays["option_stages"] == index))
            for index in range(len(STAGE_NAMES))
        },
        "reward_mean": float(np.mean(rewards)),
        "reward_median": float(np.median(rewards)),
        "reward_min": float(np.min(rewards)),
        "reward_max": float(np.max(rewards)),
        "source_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in args.replay
        },
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    args.output.with_suffix(".json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: metadata[key] for key in (
        "episodes", "rows", "cleaned_source_actions", "option_active_rows",
        "reward_mean", "reward_median", "reward_min", "reward_max", "elapsed_seconds",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
