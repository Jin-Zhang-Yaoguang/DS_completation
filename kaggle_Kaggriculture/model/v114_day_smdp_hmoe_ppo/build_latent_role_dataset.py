"""Build the V114 V6 dataset with an absorbing market STOP tail.

The input may be either the untouched Stage35 teacher dataset or a V114
per-slot derivative.  All unrelated source arrays are copied.  Existing
``option_id`` and ``unit_roles`` arrays are preserved and validated; when they
are absent they are derived from the recorded teacher family and unit action.

For every market sequence the first active STOP is an absorbing boundary.  The
boundary and every later slot are supervised as active STOP actions with zero
quantity and the STOP auxiliary role.  A teacher sequence that used all market
slots and therefore has no STOP is preserved verbatim; it has no unobserved
tail that can be labelled without overwriting a real teacher order.  No
strategy checkpoint or parent policy is inherited by this transformation.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402


OPTION_IDS = {
    "demand-timing-preemption": 0,
    "procurement-slot-ordering": 1,
    "production-route-router": 2,
}
UNIT_ROLE_NAMES = ("PASS_SAFE", "CROP", "ANIMAL", "LOGISTICS")
MARKET_ROLE_NAMES = ("STOP", "PROCURE_EXPAND", "SELL")
STOP_ROLE = 0
TERMINAL_STEP = 671
REQUIRED_KEYS = {
    "teacher_family",
    "unit_tokens",
    "unit_mask",
    "market_tokens",
    "market_quantities",
    "market_mask",
    "episode",
    "step",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unit_role(token: int) -> int:
    name = space.UNIT_TOKENS[int(token)]
    if name == "PASS":
        return 0
    if name in {"WATER", "HARVEST", "FERTILIZE", "DIG"} or name.startswith("PLANT:"):
        return 1
    if name in {"BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE"}:
        return 2
    return 3


def market_role(token: int) -> int:
    name = space.MARKET_TOKENS[int(token)]
    if name == "STOP":
        return STOP_ROLE
    if name.startswith("SELL:"):
        return 2
    return 1


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


def _validate_row_alignment(arrays: dict[str, np.ndarray]) -> int:
    missing = REQUIRED_KEYS - set(arrays)
    if missing:
        raise ValueError(f"teacher dataset missing required keys: {sorted(missing)}")
    rows = len(arrays["teacher_family"])
    for key, array in arrays.items():
        if array.ndim == 0 or len(array) != rows:
            raise ValueError(f"{key} is not row-aligned with the teacher dataset")
    if arrays["teacher_family"].ndim != 1:
        raise ValueError("teacher_family must be one-dimensional")
    if arrays["episode"].ndim != 1 or arrays["step"].ndim != 1:
        raise ValueError("episode and step must be one-dimensional")
    if arrays["unit_tokens"].ndim != 2 or arrays["unit_mask"].shape != arrays["unit_tokens"].shape:
        raise ValueError("unit_tokens and unit_mask must be aligned rank-2 arrays")
    market_shape = arrays["market_tokens"].shape
    if arrays["market_tokens"].ndim != 2:
        raise ValueError("market_tokens must be rank-2")
    for key in ("market_quantities", "market_mask"):
        if arrays[key].shape != market_shape:
            raise ValueError(f"{key} shape must match market_tokens")
    return rows


def _derive_or_validate_options(arrays: dict[str, np.ndarray], families: np.ndarray) -> np.ndarray:
    expected = np.fromiter(
        (OPTION_IDS[family] for family in families),
        dtype=np.int8,
        count=len(families),
    )
    if "option_id" not in arrays:
        return expected
    existing = np.asarray(arrays["option_id"])
    if existing.ndim != 1 or existing.shape != expected.shape:
        raise ValueError("option_id must be one-dimensional and row-aligned")
    if not np.array_equal(existing.astype(np.int8), expected):
        raise ValueError("existing option_id conflicts with teacher_family")
    return existing.copy()


def _derive_or_preserve_unit_roles(arrays: dict[str, np.ndarray]) -> tuple[np.ndarray, bool]:
    unit_tokens = np.asarray(arrays["unit_tokens"])
    if "unit_roles" in arrays:
        existing = np.asarray(arrays["unit_roles"])
        if existing.shape != unit_tokens.shape:
            raise ValueError("unit_roles shape must match unit_tokens")
        if np.any((existing < 0) | (existing >= len(UNIT_ROLE_NAMES))):
            raise ValueError("unit_roles contains an unknown auxiliary label")
        return existing.copy(), True
    roles = np.vectorize(unit_role, otypes=[np.int8])(unit_tokens)
    roles[np.asarray(arrays["unit_mask"]) == 0] = 0
    return roles.astype(np.int8), False


def _episode_counts(families: np.ndarray, episodes: np.ndarray) -> dict[str, int]:
    return {
        family: int(len(np.unique(episodes[families == family])))
        for family in OPTION_IDS
    }


def build_latent_role_dataset(
    source: Path,
    output: Path,
    manifest: Path | None = None,
) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    manifest = (manifest or output.with_suffix(".manifest.json")).resolve()
    if source == output:
        raise ValueError("output must differ from source")
    if output.suffix != ".npz":
        raise ValueError("output must use the .npz suffix")
    if manifest in {source, output}:
        raise ValueError("manifest must differ from source and output")

    source_digest = sha256_file(source)
    with np.load(source, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    rows = _validate_row_alignment(arrays)

    families = np.asarray(arrays["teacher_family"]).astype(str)
    unknown = sorted(set(families.tolist()) - set(OPTION_IDS))
    if unknown:
        raise ValueError(f"unknown teacher families: {unknown}")
    missing_families = sorted(set(OPTION_IDS) - set(families.tolist()))
    if missing_families:
        raise ValueError(f"dataset does not contain all three teacher families: {missing_families}")

    option_id = _derive_or_validate_options(arrays, families)
    unit_roles, unit_roles_preserved = _derive_or_preserve_unit_roles(arrays)

    market_tokens = np.asarray(arrays["market_tokens"]).copy()
    market_quantities = np.asarray(arrays["market_quantities"]).copy()
    original_market_mask = np.asarray(arrays["market_mask"]).copy()
    expanded_market_mask = original_market_mask.copy()
    market_roles = np.vectorize(market_role, otypes=[np.int8])(market_tokens)
    market_roles[original_market_mask == 0] = STOP_ROLE
    stop_token = int(space.MARKET_INDEX["STOP"])

    first_stop_slots = np.empty(rows, dtype=np.int16)
    added_by_family: Counter[str] = Counter()
    full_without_stop_by_family: Counter[str] = Counter()
    rewritten_tail_slots = 0
    for row in range(rows):
        active_stop = np.flatnonzero(
            (original_market_mask[row] != 0) & (market_tokens[row] == stop_token)
        )
        if active_stop.size == 0:
            if not np.all(original_market_mask[row] != 0):
                raise ValueError(
                    f"market row {row} has neither an active STOP boundary nor a full market sequence"
                )
            first_stop_slots[row] = -1
            full_without_stop_by_family[str(families[row])] += 1
            continue
        first_stop = int(active_stop[0])
        if np.any(original_market_mask[row, first_stop + 1:] != 0):
            raise ValueError(f"market row {row} has active actions after its first STOP")
        first_stop_slots[row] = first_stop
        tail = slice(first_stop, market_tokens.shape[1])
        added = int(np.count_nonzero(original_market_mask[row, first_stop + 1:] == 0))
        added_by_family[str(families[row])] += added
        rewritten_tail_slots += market_tokens.shape[1] - first_stop
        expanded_market_mask[row, tail] = 1
        market_tokens[row, tail] = stop_token
        market_quantities[row, tail] = 0
        market_roles[row, tail] = STOP_ROLE

    arrays["option_id"] = option_id
    arrays["unit_roles"] = unit_roles
    arrays["market_tokens"] = market_tokens
    arrays["market_quantities"] = market_quantities
    arrays["market_mask"] = expanded_market_mask
    arrays["market_roles"] = market_roles.astype(np.int8)
    arrays["terminal_flag"] = (np.asarray(arrays["step"]) >= TERMINAL_STEP).astype(np.int8)
    _atomic_npz(output, arrays)

    original_active = int(np.count_nonzero(original_market_mask))
    expanded_active = int(np.count_nonzero(expanded_market_mask))
    added_active = expanded_active - original_active
    family_rows = {
        family: int(np.count_nonzero(families == family))
        for family in OPTION_IDS
    }
    family_episodes = _episode_counts(families, np.asarray(arrays["episode"]))
    terminal_rows = int(np.count_nonzero(arrays["terminal_flag"]))
    report: dict[str, Any] = {
        "schema": "kaggriculture-v114-v6-latent-role-absorbing-stop-dataset-v1",
        "model_id": "v114_day_smdp_hmoe_ppo_v6",
        "strategy_parent": None,
        "inherits_v113_checkpoint": False,
        "source_checkpoint": None,
        "checkpoint_inheritance": "NONE_DATASET_TRANSFORMATION_ONLY",
        "online_historical_agent_fallback": False,
        "source": {
            "path": str(source),
            "sha256": source_digest,
            "kind": "per_slot" if "option_id" in arrays and unit_roles_preserved else "teacher",
        },
        "output": {
            "path": str(output),
            "sha256": sha256_file(output),
            "compression": "np.savez_compressed",
        },
        "rows": rows,
        "episodes": int(len(np.unique(arrays["episode"]))),
        "option_contract": dict(OPTION_IDS),
        "family_balance": {
            "row_counts": family_rows,
            "episode_counts": family_episodes,
            "rows_exactly_balanced": len(set(family_rows.values())) == 1,
            "episodes_exactly_balanced": len(set(family_episodes.values())) == 1,
        },
        "unit_role_auxiliary_labels": {
            "preserved_from_source": unit_roles_preserved,
            "contract": {str(index): name for index, name in enumerate(UNIT_ROLE_NAMES)},
        },
        "market_absorbing_stop": {
            "contract": (
                "first active STOP and every later slot are active STOP with quantity 0 and role STOP; "
                "full teacher sequences without STOP are preserved"
            ),
            "slots_per_row": int(market_tokens.shape[1]),
            "original_mask_active": original_active,
            "expanded_mask_active": expanded_active,
            "stop_tail_added_active": added_active,
            "stop_tail_added_by_family": {
                family: int(added_by_family[family]) for family in OPTION_IDS
            },
            "full_sequences_without_stop": int(np.count_nonzero(first_stop_slots < 0)),
            "full_sequences_without_stop_by_family": {
                family: int(full_without_stop_by_family[family]) for family in OPTION_IDS
            },
            "absorbing_tail_slots_total": int(rewritten_tail_slots),
            "first_stop_slot_counts": {
                str(slot): int(count)
                for slot, count in sorted(Counter(first_stop_slots[first_stop_slots >= 0].astype(int).tolist()).items())
            },
            "all_rows_fully_active_after_transform": bool(np.all(expanded_market_mask != 0)),
            "stop_token": stop_token,
            "stop_role": STOP_ROLE,
        },
        "terminal": {
            "boundary": "official observation step >= 671 (last 48 decisions)",
            "step_gte": TERMINAL_STEP,
            "terminal_rows": terminal_rows,
            "non_terminal_rows": rows - terminal_rows,
        },
        "arrays": {
            key: {"shape": list(array.shape), "dtype": str(array.dtype)}
            for key, array in arrays.items()
        },
        "qualification_status": "DATASET_ONLY_NOT_QUALIFIED_NOT_GOLD",
    }
    _atomic_json(manifest, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Teacher or per-slot .npz dataset")
    parser.add_argument("--output", type=Path, required=True, help="Compressed V6 output .npz")
    parser.add_argument("--manifest", type=Path, help="Defaults to <output stem>.manifest.json")
    args = parser.parse_args()
    report = build_latent_role_dataset(args.source, args.output, args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
