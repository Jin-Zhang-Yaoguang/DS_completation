"""Map each closed-loop teacher lineage to a coherent full-season expert pair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np


LINEAGE_SLOTS = {
    "demand-timing-preemption": 0,
    "procurement-slot-ordering": 1,
    "production-route-router": 2,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    source_sha = sha256(args.source)
    with np.load(args.source, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    families = arrays["teacher_family"].astype(str)
    unknown = sorted(set(families) - set(LINEAGE_SLOTS))
    missing = sorted(set(LINEAGE_SLOTS) - set(families))
    if unknown or missing:
        raise ValueError(f"teacher lineage contract mismatch: unknown={unknown}, missing={missing}")
    labels = np.asarray([LINEAGE_SLOTS[value] for value in families], dtype=np.int16)
    arrays["unit_expert"] = labels.copy()
    arrays["market_expert"] = labels.copy()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    output_sha = sha256(args.output)
    counts = {family: int(np.sum(families == family)) for family in LINEAGE_SLOTS}
    report = {
        "schema": "kaggriculture-v114-lineage-expert-dataset-v1",
        "source": str(args.source),
        "source_sha256": source_sha,
        "output": str(args.output),
        "output_sha256": output_sha,
        "rows": int(len(labels)),
        "episodes": int(len(np.unique(arrays["episode"]))),
        "lineage_expert_contract": {
            family: {
                "unit_slot": slot,
                "market_slot": slot,
                "rows": counts[family],
                "scope": "complete-season-production-logistics-plus-market-cash",
            }
            for family, slot in LINEAGE_SLOTS.items()
        },
        "strategy_parent": None,
        "inherits_v113_checkpoint": False,
        "online_historical_agent_fallback": False,
        "qualification_status": "DATASET_ONLY_NOT_QUALIFIED_NOT_GOLD",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.manifest.parent, delete=False) as sink:
        json.dump(report, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
