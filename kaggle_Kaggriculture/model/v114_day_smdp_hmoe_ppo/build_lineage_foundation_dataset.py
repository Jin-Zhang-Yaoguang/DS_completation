"""Build one closed-loop lineage dataset for a V114 foundation expert.

Historical agents are used only as offline teachers.  Rows from different
behavior families are never mixed.  A deterministic pre-action history vector
is appended so the learned policy can preserve multi-day commitments without
calling the teacher at serving time.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

from action_history import ActionHistoryState, HISTORY_FEATURES, augment_global  # noqa: E402


REQUIRED_KEYS = {
    "global", "episode", "seat", "step", "teacher_family", "teacher_id",
    "unit_tokens", "market_tokens", "market_quantities", "market_mask",
}
STEPS_PER_GAME = 719


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def build_lineage_dataset(source: Path, output: Path, manifest: Path, family: str) -> dict:
    with np.load(source, allow_pickle=False) as archive:
        missing = REQUIRED_KEYS - set(archive.files)
        if missing:
            raise ValueError(f"source dataset missing keys: {sorted(missing)}")
        source_family = np.asarray(archive["teacher_family"]).astype(str)
        selected = np.flatnonzero(source_family == family)
        if len(selected) == 0:
            raise ValueError(f"teacher family not found: {family}")
        arrays = {key: np.asarray(archive[key][selected]) for key in archive.files}

    order = np.lexsort((arrays["step"], arrays["seat"], arrays["episode"]))
    arrays = {key: value[order] for key, value in arrays.items()}
    trajectory_keys = list(zip(arrays["episode"].astype(int), arrays["seat"].astype(int)))
    counts = Counter(trajectory_keys)
    invalid = {str(key): count for key, count in counts.items() if count != STEPS_PER_GAME}
    if invalid:
        raise ValueError(f"incomplete lineage trajectories: {invalid}")

    history = ActionHistoryState()
    augmented: list[np.ndarray] = []
    previous_key = None
    previous_step = -1
    for index, key in enumerate(trajectory_keys):
        step = int(arrays["step"][index])
        if key != previous_key:
            if step != 0:
                raise ValueError(f"trajectory {key} does not start at step 0")
            history.reset()
        elif step != previous_step + 1:
            raise ValueError(f"non-contiguous trajectory {key}: {previous_step} -> {step}")
        augmented.append(augment_global(arrays["global"][index], history))
        history.update_tokens(
            arrays["unit_tokens"][index], arrays["market_tokens"][index],
            arrays["market_quantities"][index],
        )
        previous_key, previous_step = key, step
    base_global_features = int(arrays["global"].shape[1])
    arrays["global"] = np.asarray(augmented, dtype=np.float32)

    # The upstream V114 latent-role transform makes STOP absorbing within each
    # market action.  Fail closed if a later slot becomes active after an
    # inactive slot, which would reintroduce an unsupervised decoder tail.
    active = np.asarray(arrays["market_mask"], dtype=np.uint8)
    non_monotone_masks = int(np.count_nonzero(np.diff(active.astype(np.int8), axis=1) > 0))
    if non_monotone_masks:
        raise ValueError("market mask contains inactive-to-active transitions")

    _atomic_npz(output, arrays)
    teachers, teacher_counts = np.unique(arrays["teacher_id"].astype(str), return_counts=True)
    report = {
        "schema": "kaggriculture-v114-lineage-foundation-dataset-v1",
        "source": str(source.resolve()),
        "source_sha256": sha256_file(source),
        "output": str(output.resolve()),
        "output_sha256": sha256_file(output),
        "teacher_family": family,
        "teacher_ids": {str(k): int(v) for k, v in zip(teachers, teacher_counts)},
        "rows": int(len(arrays["step"])),
        "seed_groups": int(len(np.unique(arrays["episode"]))),
        "games": int(len(counts)),
        "steps_per_game": STEPS_PER_GAME,
        "base_global_features": base_global_features,
        "history_features": HISTORY_FEATURES,
        "augmented_global_features": int(arrays["global"].shape[1]),
        "teacher_executed_closed_loop_only": True,
        "historical_agent_online_action_source": False,
        "strategy_parent": None,
        "qualification_status": "OFFLINE_DATASET_ONLY_NOT_QUALIFIED_NOT_GOLD",
    }
    _atomic_json(manifest, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--family", required=True)
    args = parser.parse_args()
    report = build_lineage_dataset(args.source, args.output, args.manifest, args.family)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
