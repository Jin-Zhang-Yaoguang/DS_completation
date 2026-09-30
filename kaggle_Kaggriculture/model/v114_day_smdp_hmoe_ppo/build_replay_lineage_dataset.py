"""Build a single-lineage V114 BC dataset from downloaded Kaggriculture Replay.

Only the submitted agent's seat from each episode is used. The observation at
step ``t`` is paired with the action stored at Replay index ``t + 1``. Expert
labels are a pre-registered causal time-phase contract and never inspect the
current action, teacher identity, future state, or final score.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import time

import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402
import features  # noqa: E402
from action_history import ActionHistoryState, HISTORY_FEATURES, augment_global  # noqa: E402


STEPS_PER_GAME = 719
EPISODE_PATTERN = re.compile(r"episode-(\d+)-replay\.json$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_id(episode_id: int) -> int:
    bucket = int(
        hashlib.sha256(f"v114-replay-lineage:{episode_id}".encode()).hexdigest()[:8], 16
    ) % 100
    return 0 if bucket < 70 else (1 if bucket < 85 else 2)


def causal_phase_labels(step: int) -> tuple[int, int]:
    """Return deployment-observable phase labels compatible with router masks."""
    if step >= 671:
        return 5, 5
    if step < 72:
        unit = 4       # opening setup
    elif step < 216:
        unit = 2       # route construction and movement
    elif step < 480:
        unit = 0       # main production
    else:
        unit = 1       # mature-route maintenance
    market = 4 if step < 480 else 3  # procurement then liquidation/control
    return unit, market


def episode_id(path: Path) -> int:
    match = EPISODE_PATTERN.search(path.name)
    if match is None:
        raise ValueError(f"invalid Replay filename: {path.name}")
    return int(match.group(1))


def load_agent_seats(sync_manifest: Path) -> dict[int, int]:
    payload = json.loads(sync_manifest.read_text(encoding="utf-8"))
    seats: dict[int, int] = {}
    for row in payload.get("results", []):
        if row.get("agent_index") is None:
            continue
        current = int(row["agent_index"])
        if current not in (0, 1):
            raise ValueError(f"invalid agent seat: {row}")
        identity = int(row["episode_id"])
        if identity in seats and seats[identity] != current:
            raise ValueError(f"conflicting agent seats for episode {identity}")
        seats[identity] = current
    return seats


def replay_inventory(replay_root: Path, sync_manifest: Path) -> tuple[list[Path], dict[int, int], str]:
    seats = load_agent_seats(sync_manifest)
    files = sorted(replay_root.glob("episode-*-replay.json"), key=episode_id)
    if not files:
        raise ValueError(f"no Replay files under {replay_root}")
    file_ids = [episode_id(path) for path in files]
    missing = sorted(set(file_ids) - set(seats))
    extra = sorted(set(seats) - set(file_ids))
    if missing or extra:
        raise ValueError(f"Replay/manifest mismatch: missing seats={missing}, missing files={extra}")
    digest = hashlib.sha256()
    for path in files:
        identity = episode_id(path)
        digest.update(f"{identity}:{sha256_file(path)}\n".encode())
    return files, seats, digest.hexdigest()


def _atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", suffix=".npz", dir=path.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(path)


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def build(
    replay_root: Path,
    sync_manifest: Path,
    output: Path,
    report_path: Path,
    lineage_id: str,
    teacher_id: str,
    teacher_sha256: str,
) -> dict:
    started = time.time()
    files, seats, bundle_sha = replay_inventory(replay_root, sync_manifest)
    rows: dict[str, list] = {key: [] for key in (
        "global", "board", "units", "unit_mask", "unit_tokens", "unit_quantities",
        "market_tokens", "market_quantities", "market_mask", "expert", "unit_expert",
        "market_expert", "value", "split", "episode", "step", "seat", "teacher_id",
        "teacher_family", "teacher_sha256",
    )}
    cleaning_count = 0
    action_count = 0
    phase_counts: Counter = Counter()
    seat_counts: Counter = Counter()
    terminal_margins: list[float] = []
    for path in files:
        identity = episode_id(path)
        seat = seats[identity]
        replay = json.loads(path.read_text(encoding="utf-8"))
        steps = replay.get("steps") or []
        if len(steps) != STEPS_PER_GAME + 1:
            raise ValueError(f"episode {identity} has {len(steps)} Replay indices")
        rewards = [float(steps[-1][index].get("reward") or 0.0) for index in (0, 1)]
        margin = rewards[seat] - rewards[1 - seat]
        terminal_margins.append(margin)
        value = float(np.sign(margin) + 0.05 * np.tanh(margin / 25000.0))
        history = ActionHistoryState()
        for action_index in range(1, len(steps)):
            step = action_index - 1
            obs = dict(steps[action_index - 1][seat].get("observation") or {})
            obs["step"] = step
            source = space.normalise_action(
                steps[action_index][seat].get("action") or {}, space.unit_count(obs) - 1
            )
            clean = space.decode_action(obs, space.encode_action(obs, source))
            cleaning_count += int(clean != source)
            action_count += 1
            encoded = space.encode_action(obs, clean)
            state = features.encode_observation(obs)
            state["global"] = augment_global(state["global"], history)

            unit_tokens = np.full(
                (features.MAX_UNITS,), space.UNIT_INDEX["PASS"], dtype=np.int16
            )
            unit_quantities = np.zeros((features.MAX_UNITS,), dtype=np.int16)
            unit_count = min(features.MAX_UNITS, len(encoded["unit_tokens"]))
            unit_tokens[:unit_count] = encoded["unit_tokens"][:unit_count]
            unit_quantities[:unit_count] = encoded["unit_quantities"][:unit_count]
            market_tokens = np.asarray(encoded["market_tokens"], dtype=np.int16)
            market_quantities = np.asarray(encoded["market_quantities"], dtype=np.int16)
            market_mask = np.ones((space.MAX_MARKET_SLOTS,), dtype=np.float32)
            unit_expert, market_expert = causal_phase_labels(step)

            for key in ("global", "board", "units", "unit_mask"):
                rows[key].append(state[key])
            rows["unit_tokens"].append(unit_tokens)
            rows["unit_quantities"].append(unit_quantities)
            rows["market_tokens"].append(market_tokens)
            rows["market_quantities"].append(market_quantities)
            rows["market_mask"].append(market_mask)
            rows["expert"].append(unit_expert)
            rows["unit_expert"].append(unit_expert)
            rows["market_expert"].append(market_expert)
            rows["value"].append(value)
            rows["split"].append(split_id(identity))
            rows["episode"].append(identity)
            rows["step"].append(step)
            rows["seat"].append(seat)
            rows["teacher_id"].append(teacher_id)
            rows["teacher_family"].append(lineage_id)
            rows["teacher_sha256"].append(teacher_sha256)
            phase_counts[(unit_expert, market_expert)] += 1
            seat_counts[seat] += 1
            history.update_tokens(unit_tokens, market_tokens, market_quantities)

    arrays = {key: np.asarray(value) for key, value in rows.items()}
    for key in ("global", "board", "units"):
        arrays[key] = arrays[key].astype(np.float16)
    for key in ("unit_mask", "market_mask", "value"):
        arrays[key] = arrays[key].astype(np.float32)
    for key in (
        "unit_tokens", "unit_quantities", "market_tokens", "market_quantities",
        "expert", "unit_expert", "market_expert", "split", "step", "seat",
    ):
        arrays[key] = arrays[key].astype(np.int16)
    arrays["episode"] = arrays["episode"].astype(np.int64)
    _atomic_npz(output, arrays)
    report = {
        "schema": "kaggriculture-v114-single-replay-lineage-dataset-v1",
        "lineage_id": lineage_id,
        "teacher_id": teacher_id,
        "teacher_agent_sha256": teacher_sha256,
        "sync_manifest": str(sync_manifest.resolve()),
        "sync_manifest_sha256": sha256_file(sync_manifest),
        "replay_root": str(replay_root.resolve()),
        "replay_bundle_sha256": bundle_sha,
        "episodes": len(files),
        "games": len(files),
        "rows": int(len(arrays["step"])),
        "steps_per_game": STEPS_PER_GAME,
        "seat_rows": {str(key): int(value) for key, value in sorted(seat_counts.items())},
        "split_games": {
            name: int(len(np.unique(arrays["episode"][arrays["split"] == index])))
            for index, name in enumerate(("train", "development", "blind"))
        },
        "causal_phase_contract": {
            "unit": {"0-71": 4, "72-215": 2, "216-479": 0, "480-670": 1, "671-718": 5},
            "market": {"0-479": 4, "480-670": 3, "671-718": 5},
            "uses_current_action": False,
            "uses_future_state_or_score": False,
            "uses_teacher_identity": False,
        },
        "phase_rows": {
            f"unit_{unit}_market_{market}": int(count)
            for (unit, market), count in sorted(phase_counts.items())
        },
        "base_global_features": features.GLOBAL_FEATURES,
        "history_features": HISTORY_FEATURES,
        "augmented_global_features": int(arrays["global"].shape[1]),
        "absorbing_market_stop_tail": True,
        "action_cleaning_count": cleaning_count,
        "action_cleaning_rate": cleaning_count / max(1, action_count),
        "mean_teacher_terminal_margin": float(np.mean(terminal_margins)),
        "output": str(output.resolve()),
        "output_sha256": sha256_file(output),
        "strategy_parent": None,
        "historical_agent_online_action_source": False,
        "qualification_status": "OFFLINE_DATASET_ONLY_NOT_QUALIFIED_NOT_GOLD",
        "elapsed_seconds": time.time() - started,
    }
    _atomic_json(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--sync-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--lineage-id", required=True)
    parser.add_argument("--teacher-id", required=True)
    parser.add_argument("--teacher-sha256", required=True)
    args = parser.parse_args()
    report = build(
        args.replay_root, args.sync_manifest, args.output, args.report,
        args.lineage_id, args.teacher_id, args.teacher_sha256,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
