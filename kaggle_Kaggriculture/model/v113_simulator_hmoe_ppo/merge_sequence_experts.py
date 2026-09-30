"""Merge independently trained unit/market expert slices onto one frozen base."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from flax import serialization, traverse_util
import numpy as np

from model_sequence_action import HIDDEN, NUM_EXPERTS


PROJECTION_MODULES = {"unit_expert_projection", "market_expert_projection"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return serialization.msgpack_restore(path.read_bytes())


def assert_shared_params_equal(base: dict, candidate: dict, label: str) -> None:
    base_flat = traverse_util.flatten_dict(base["params"])
    candidate_flat = traverse_util.flatten_dict(candidate["params"])
    if set(base_flat) != set(candidate_flat):
        raise ValueError(f"{label} parameter tree differs from base")
    mismatches = []
    for path, base_value in base_flat.items():
        if path[0] in PROJECTION_MODULES:
            continue
        candidate_value = candidate_flat[path]
        if not np.array_equal(np.asarray(base_value), np.asarray(candidate_value)):
            mismatches.append("/".join(path))
    if mismatches:
        raise ValueError(
            f"{label} changed frozen shared parameters: {mismatches[:8]}"
        )


def copy_slice(target: dict, source: dict, module: str, expert: int) -> None:
    selected = slice(expert * HIDDEN, (expert + 1) * HIDDEN)
    for field in ("kernel", "bias"):
        target_value = np.asarray(target["params"][module][field]).copy()
        source_value = np.asarray(source["params"][module][field])
        if target_value.shape != source_value.shape:
            raise ValueError(f"shape mismatch for {module}/{field}")
        if field == "kernel":
            target_value[:, selected] = source_value[:, selected]
        else:
            target_value[selected] = source_value[selected]
        target["params"][module][field] = target_value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--unit-checkpoint", type=Path, required=True)
    parser.add_argument("--unit-expert", type=int, required=True, choices=range(NUM_EXPERTS))
    parser.add_argument("--market-checkpoint", type=Path, required=True)
    parser.add_argument("--market-expert", type=int, required=True, choices=range(NUM_EXPERTS))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base = load(args.base)
    unit = load(args.unit_checkpoint)
    market = load(args.market_checkpoint)
    assert_shared_params_equal(base, unit, "unit checkpoint")
    assert_shared_params_equal(base, market, "market checkpoint")
    copy_slice(base, unit, "unit_expert_projection", args.unit_expert)
    copy_slice(base, market, "market_expert_projection", args.market_expert)

    manifest = {
        "schema": "kaggriculture-v113-sequence-expert-merge-v1",
        "base": str(args.base),
        "base_sha256": sha256(args.base),
        "unit_checkpoint": str(args.unit_checkpoint),
        "unit_checkpoint_sha256": sha256(args.unit_checkpoint),
        "unit_expert": args.unit_expert,
        "market_checkpoint": str(args.market_checkpoint),
        "market_checkpoint_sha256": sha256(args.market_checkpoint),
        "market_expert": args.market_expert,
        "shared_params_equal": True,
    }
    base["expert_merge"] = manifest
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(base))
        temporary = Path(sink.name)
    temporary.replace(args.output)
    args.output.with_suffix(".json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
