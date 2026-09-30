"""Relabel closed-loop teacher trajectories into complete V114 responsibility experts.

The V113 labels identify phase/functional heads and therefore cannot be forced for
an entire season.  V114 instead trains two parallel, full-season responsibilities:

* unit head 0: PRODUCTION_LOGISTICS, trained on every unit action;
* market head 1: MARKET_CASH, trained on every market action.

No checkpoint or online teacher policy is copied by this transformation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--unit-slot", type=int, default=0)
    parser.add_argument("--market-slot", type=int, default=1)
    args = parser.parse_args()

    if args.unit_slot == args.market_slot:
        parser.error("unit and market responsibilities must use different slots")
    source_sha = sha256(args.source)
    with np.load(args.source, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    required = {"unit_expert", "market_expert", "episode", "teacher_family", "unit_tokens", "market_tokens"}
    missing = required - set(arrays)
    if missing:
        raise ValueError(f"source dataset missing keys: {sorted(missing)}")

    source_unit_counts = np.bincount(arrays["unit_expert"].astype(np.int64), minlength=6)
    source_market_counts = np.bincount(arrays["market_expert"].astype(np.int64), minlength=6)
    arrays["unit_expert"] = np.full_like(arrays["unit_expert"], args.unit_slot)
    arrays["market_expert"] = np.full_like(arrays["market_expert"], args.market_slot)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    output_sha = sha256(args.output)

    families, family_counts = np.unique(arrays["teacher_family"].astype(str), return_counts=True)
    report = {
        "schema": "kaggriculture-v114-responsibility-bc-dataset-v1",
        "source": str(args.source),
        "source_sha256": source_sha,
        "output": str(args.output),
        "output_sha256": output_sha,
        "rows": int(len(arrays["episode"])),
        "episodes": int(len(np.unique(arrays["episode"]))),
        "teacher_family_rows": {family: int(count) for family, count in zip(families, family_counts)},
        "source_unit_expert_counts": source_unit_counts.tolist(),
        "source_market_expert_counts": source_market_counts.tolist(),
        "v114_responsibilities": {
            "unit": {"slot": args.unit_slot, "name": "PRODUCTION_LOGISTICS", "rows": int(len(arrays["episode"]))},
            "market": {"slot": args.market_slot, "name": "MARKET_CASH", "rows": int(len(arrays["episode"]))},
        },
        "strategy_parent": None,
        "inherits_v113_checkpoint": False,
        "online_historical_agent_fallback": False,
        "qualification_status": "DATASET_ONLY_NOT_QUALIFIED_NOT_GOLD",
    }
    atomic_json(args.manifest, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
