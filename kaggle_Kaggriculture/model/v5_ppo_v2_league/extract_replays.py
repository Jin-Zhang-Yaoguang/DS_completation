"""Extract daily public observation/action records from Kaggle replay JSON."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import main


def action_hash(action):
    raw = json.dumps(action or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def extract(directory: Path, output: Path):
    features, actions, hashes, seeds, episodes, seats, teams = [], [], [], [], [], [], []
    for path in sorted(directory.glob("episode-*-replay.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        steps = payload.get("steps", [])
        info = payload.get("info", {})
        for seat in (0, 1):
            history = {}
            macro = main.DEFAULT_MACRO.copy()
            for day in range(30):
                step = steps[min(day * 24, len(steps) - 1)][seat]
                obs = step.get("observation", {})
                obs["player"] = seat
                features.append(main.encode_observation(obs, history, macro))
                action_rows = [steps[day * 24 + hour][seat].get("action", {}) for hour in range(min(24, len(steps) - day * 24))]
                actions.append(json.dumps(action_rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
                hashes.append(action_hash(action_rows))
                seeds.append(int(info.get("seed") or payload.get("configuration", {}).get("seed") or 0))
                episodes.append(str(payload.get("id") or path.stem))
                seats.append(seat)
                teams.append(json.dumps(info.get("TeamNames", []), ensure_ascii=False))
                history = main.update_history(obs, macro)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, features=np.asarray(features, dtype=np.float32), action_json=np.asarray(actions), action_hash=np.asarray(hashes), seeds=np.asarray(seeds, dtype=np.int64), episode_ids=np.asarray(episodes), seats=np.asarray(seats, dtype=np.int8), teams=np.asarray(teams))
    return {"schema": "kaggriculture-ppo-v2-replay-daily-1", "episodes": len(set(episodes)), "seat_episodes": len(features) // 30, "daily_rows": len(features), "output": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent / "data" / "replays" / "champion")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "data" / "replay_daily.npz")
    args = parser.parse_args()
    print(json.dumps(extract(args.directory, args.output), ensure_ascii=False, indent=2))
