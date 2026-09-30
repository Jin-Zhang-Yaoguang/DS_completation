"""Add lineage-level nested-option labels to a Stage35 dataset.

The Stage35 functional ``unit_expert`` and ``market_expert`` labels are copied
unchanged.  ``option_id`` is derived only from the recorded teacher behavior
family, so the new high-level option and the existing low-level responsibility
labels remain separate supervision targets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

import numpy as np


OPTION_IDS = {
    "demand-timing-preemption": 0,
    "procurement-slot-ordering": 1,
    "production-route-router": 2,
}
REQUIRED_KEYS = {"unit_expert", "market_expert", "teacher_family"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def array_sha256(array: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(json.dumps(array.shape).encode("ascii"))
    digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", suffix=".npz", dir=path.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def _validate_source(arrays: dict[str, np.ndarray]) -> int:
    missing = REQUIRED_KEYS - set(arrays)
    if missing:
        raise ValueError(f"Stage35 dataset missing required keys: {sorted(missing)}")
    if "option_id" in arrays:
        raise ValueError("source dataset already contains option_id")

    rows = len(arrays["unit_expert"])
    for key in REQUIRED_KEYS:
        if arrays[key].ndim != 1:
            raise ValueError(f"{key} must be one-dimensional")
        if len(arrays[key]) != rows:
            raise ValueError(f"{key} row count does not match unit_expert")
    for key, array in arrays.items():
        if array.ndim == 0 or len(array) != rows:
            raise ValueError(f"{key} is not row-aligned with the Stage35 dataset")
    return rows


def build_nested_option_dataset(
    source: Path,
    output: Path,
    manifest: Path | None = None,
) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    manifest = (manifest or output.with_suffix(".manifest.json")).resolve()
    if source == output:
        raise ValueError("output must differ from the Stage35 source")
    if output.suffix != ".npz":
        raise ValueError("output must use the .npz suffix")
    if manifest in {source, output}:
        raise ValueError("manifest must differ from source and output")

    source_digest = sha256_file(source)
    with np.load(source, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    rows = _validate_source(arrays)

    families = np.asarray(arrays["teacher_family"]).astype(str)
    unknown = sorted(set(families.tolist()) - set(OPTION_IDS))
    if unknown:
        raise ValueError(f"unknown Stage35 teacher families: {unknown}")
    option_id = np.fromiter(
        (OPTION_IDS[family] for family in families),
        dtype=np.int8,
        count=rows,
    )

    original_unit_expert = arrays["unit_expert"].copy()
    original_market_expert = arrays["market_expert"].copy()
    arrays["option_id"] = option_id
    _atomic_npz(output, arrays)

    with np.load(output, allow_pickle=False) as written:
        unit_preserved = np.array_equal(written["unit_expert"], original_unit_expert)
        market_preserved = np.array_equal(written["market_expert"], original_market_expert)
        if not unit_preserved or not market_preserved:
            raise RuntimeError("functional expert labels changed while writing output")

    option_counts = {
        name: int(np.count_nonzero(option_id == identifier))
        for name, identifier in OPTION_IDS.items()
    }
    role_hashes = {
        "unit_expert": array_sha256(original_unit_expert),
        "market_expert": array_sha256(original_market_expert),
    }
    report: dict[str, Any] = {
        "schema": "kaggriculture-v114-nested-option-dataset-v1",
        "model_id": "v114_day_smdp_hmoe_ppo",
        "strategy_parent": None,
        "inherits_v113_checkpoint": False,
        "source_checkpoint": None,
        "checkpoint_inheritance": "NONE_DATASET_TRANSFORMATION_ONLY",
        "source": {
            "path": str(source),
            "sha256": source_digest,
            "stage": 35,
        },
        "output": {
            "path": str(output),
            "sha256": sha256_file(output),
            "compression": "np.savez_compressed",
        },
        "rows": rows,
        "option_contract": dict(OPTION_IDS),
        "option_counts": option_counts,
        "functional_role_labels": {
            "preserved": True,
            "unit_expert_sha256": role_hashes["unit_expert"],
            "market_expert_sha256": role_hashes["market_expert"],
        },
        "arrays": {
            key: {"shape": list(array.shape), "dtype": str(array.dtype)}
            for key, array in arrays.items()
        },
    }
    _atomic_json(manifest, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Stage35 .npz dataset")
    parser.add_argument("--output", type=Path, required=True, help="Compressed output .npz")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="SHA manifest; defaults to <output stem>.manifest.json",
    )
    args = parser.parse_args()
    report = build_nested_option_dataset(args.input, args.output, args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
