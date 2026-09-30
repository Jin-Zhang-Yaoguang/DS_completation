"""Shrink V113 action-head logits without changing their pre-PPO argmax policy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from flax import serialization
import numpy as np


ACTION_HEADS = (
    "unit_action_head",
    "unit_quantity_head",
    "market_action_head",
    "market_quantity_head",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--scale", type=float, default=0.1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 0.0 < args.scale <= 1.0:
        parser.error("--scale must be in (0, 1]")

    source_bytes = args.checkpoint.read_bytes()
    payload = serialization.msgpack_restore(source_bytes)
    params = dict(payload["params"])
    for head in ACTION_HEADS:
        layer = dict(params[head])
        layer["kernel"] = np.asarray(layer["kernel"]) * args.scale
        layer["bias"] = np.asarray(layer["bias"]) * args.scale
        params[head] = layer
    result = {
        **{key: value for key, value in payload.items() if key != "params"},
        "params": params,
        "architecture": "factorized-production-market-hmoe-v3-calibrated-ppo",
        "calibration": {
            "action_heads": list(ACTION_HEADS),
            "scale": args.scale,
            "source_checkpoint_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "argmax_invariant_before_ppo": True,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(args.output)
    report = {
        "schema": "kaggriculture-v113-logit-calibration-v1",
        "source": str(args.checkpoint),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "output": str(args.output),
        "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "scale": args.scale,
        "heads": list(ACTION_HEADS),
    }
    report_path = args.output.with_suffix(".json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
