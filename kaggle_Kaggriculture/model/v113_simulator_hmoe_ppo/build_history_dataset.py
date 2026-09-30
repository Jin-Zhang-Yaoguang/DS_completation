"""Append deterministic pre-action history features to a sequential teacher shard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import numpy as np

from action_history import ActionHistoryState, HISTORY_FEATURES, augment_global


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.input) as archive:
        data = {key: archive[key] for key in archive.files}
    required = {"global", "episode", "seat", "step", "unit_tokens", "market_tokens", "market_quantities"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"source shard missing keys: {sorted(missing)}")
    order = np.lexsort((data["step"], data["seat"], data["episode"]))
    if not np.array_equal(order, np.arange(len(order))):
        raise ValueError("source rows must already be sorted by episode, seat, step")
    history = ActionHistoryState()
    previous_key = None
    previous_step = -1
    augmented = []
    trajectories = 0
    for index in range(len(data["global"])):
        key = (int(data["episode"][index]), int(data["seat"][index]))
        step = int(data["step"][index])
        if key != previous_key:
            if step != 0:
                raise ValueError(f"trajectory {key} does not start at step 0")
            history.reset()
            trajectories += 1
        elif step != previous_step + 1:
            raise ValueError(f"non-contiguous trajectory {key}: {previous_step} -> {step}")
        augmented.append(augment_global(data["global"][index], history))
        history.update_tokens(
            data["unit_tokens"][index], data["market_tokens"][index],
            data["market_quantities"][index],
        )
        previous_key, previous_step = key, step
    result = dict(data)
    result["global"] = np.asarray(augmented, dtype=np.float32)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **result)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    report = {
        "schema": "kaggriculture-v113-action-history-dataset-v1",
        "source": str(args.input), "rows": len(augmented),
        "trajectories": trajectories,
        "base_global_features": int(data["global"].shape[1]),
        "history_features": HISTORY_FEATURES,
        "augmented_global_features": int(result["global"].shape[1]),
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
