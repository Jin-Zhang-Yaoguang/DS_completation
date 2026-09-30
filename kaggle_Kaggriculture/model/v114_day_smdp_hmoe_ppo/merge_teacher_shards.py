"""Merge identically-schemed teacher-executed BC shards with audit metadata."""

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    shards = []
    reports = []
    for path in args.input:
        with np.load(path, allow_pickle=False) as archive:
            shards.append({key: archive[key] for key in archive.files})
        report_path = path.parent / "multiteacher_sequence_bc_report.json"
        reports.append(json.loads(report_path.read_text(encoding="utf-8")))
    keys = set(shards[0])
    if any(set(shard) != keys for shard in shards[1:]):
        raise ValueError("teacher shards have different array schemas")
    arrays = {
        key: np.concatenate([shard[key] for shard in shards], axis=0)
        for key in sorted(keys)
    }
    episode = np.asarray(arrays["episode"], dtype=np.int64)
    # Collection shards reuse local episode ids.  Reindex by source shard so
    # grouped train/validation splits can never mix one episode across folds.
    offset = 0
    cursor = 0
    for shard in shards:
        rows = len(shard["episode"])
        local = np.asarray(shard["episode"], dtype=np.int64)
        normalized = local - local.min() + offset
        episode[cursor:cursor + rows] = normalized
        offset = int(normalized.max()) + 1
        cursor += rows
    arrays["episode"] = episode.astype(np.int32)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    family_counts = {}
    for report in reports:
        for family, values in report["family_counts"].items():
            target = family_counts.setdefault(family, {"seed_groups": 0, "games": 0, "rows": 0})
            for key in target:
                target[key] += int(values[key])
    manifest = {
        "schema": "kaggriculture-v114-merged-teacher-shards-v1",
        "inputs": [
            {"path": str(path.resolve()), "sha256": sha256(path)}
            for path in args.input
        ],
        "output": str(args.output.resolve()),
        "output_sha256": sha256(args.output),
        "rows": int(len(arrays["episode"])),
        "episodes": int(len(np.unique(arrays["episode"]))),
        "family_counts": family_counts,
        "done_done_games": int(sum(report["done_done_games"] for report in reports)),
        "unknown_tokens": {
            "canonical_total": int(sum(
                report["unknown_tokens"]["canonical"]["total"] for report in reports
            )),
        },
        "teacher_executed_closed_loop_only": True,
        "strategy_parent": None,
        "qualification_status": "DATASET_ONLY_NOT_QUALIFIED_NOT_GOLD",
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=args.manifest.parent, delete=False,
    ) as sink:
        json.dump(manifest, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(args.manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
