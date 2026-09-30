"""Reuse behavior-equivalent rollout actions under a cloned expert slot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-expert", type=int, required=True)
    parser.add_argument("--destination-expert", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.input) as archive:
        arrays = {key: archive[key] for key in archive.files}
    for key in ("unit_expert", "market_expert"):
        values = np.asarray(arrays[key])
        if not np.all(values == args.source_expert):
            raise ValueError(f"{key} is not uniformly source expert {args.source_expert}")
        arrays[key] = np.full_like(values, args.destination_expert)
    report = json.loads(args.input.with_suffix(".json").read_text(encoding="utf-8"))
    report.update({
        "schema": "kaggriculture-v113-remapped-equivalent-rollout-v1",
        "source_rollout": str(args.input),
        "source_expert": args.source_expert,
        "destination_expert": args.destination_expert,
        "requires_behavior_equivalence_qa": True,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    args.output.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
