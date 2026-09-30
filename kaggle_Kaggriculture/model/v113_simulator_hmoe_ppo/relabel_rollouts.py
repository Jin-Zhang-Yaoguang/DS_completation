"""Replace GAE with a pure episode-return advantage for long-horizon credit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--margin-scale", type=float, default=100.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    outcome = {
        (int(row["seed"]), int(row["seat"])): float(np.tanh(float(row["margin"]) / args.margin_scale))
        for row in report["rows"]
    }
    with np.load(args.rollouts) as archive:
        data = {key: archive[key] for key in archive.files}
    raw = np.asarray([
        outcome[(int(seed), int(seat))]
        for seed, seat in zip(data["episode_seed"], data["seat"])
    ], dtype=np.float32)
    data["advantage"] = (raw - raw.mean()) / max(1e-6, float(raw.std()))
    data["return_target"] = raw
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **data)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    result = {
        "schema": "kaggriculture-v113-terminal-advantage-v1",
        "transitions": len(raw), "episodes": len(outcome), "margin_scale": args.margin_scale,
        "raw_advantage_min": float(raw.min()), "raw_advantage_mean": float(raw.mean()),
        "raw_advantage_max": float(raw.max()), "raw_advantage_std": float(raw.std()),
    }
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
