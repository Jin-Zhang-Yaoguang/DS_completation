"""Add option and per-unit/per-order role labels to teacher-executed trajectories."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile

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
        return 0
    if name.startswith("SELL:"):
        return 2
    return 1


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
    required = {
        "teacher_family", "unit_tokens", "unit_mask", "market_tokens", "market_mask",
        "episode", "step",
    }
    missing = required - set(arrays)
    if missing:
        raise ValueError(f"source dataset missing keys: {sorted(missing)}")
    families = arrays["teacher_family"].astype(str)
    unknown = sorted(set(families) - set(OPTION_IDS))
    if unknown:
        raise ValueError(f"unknown teacher families: {unknown}")
    rows = len(families)
    option_ids = np.asarray([OPTION_IDS[value] for value in families], dtype=np.int8)
    unit_roles = np.vectorize(unit_role, otypes=[np.int8])(arrays["unit_tokens"])
    market_roles = np.vectorize(market_role, otypes=[np.int8])(arrays["market_tokens"])
    unit_roles[np.asarray(arrays["unit_mask"]) == 0] = 0
    market_roles[np.asarray(arrays["market_mask"]) == 0] = 0
    arrays["option_id"] = option_ids
    arrays["unit_roles"] = unit_roles.astype(np.int8)
    arrays["market_roles"] = market_roles.astype(np.int8)
    arrays["terminal_flag"] = (np.asarray(arrays["step"]) >= 671).astype(np.int8)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    unit_active = np.asarray(arrays["unit_mask"], dtype=bool)
    market_active = np.asarray(arrays["market_mask"], dtype=bool)
    unit_counts = Counter(unit_roles[unit_active].astype(int).tolist())
    market_counts = Counter(market_roles[market_active].astype(int).tolist())
    report = {
        "schema": "kaggriculture-v114-per-slot-role-dataset-v1",
        "source": str(args.source.resolve()),
        "source_sha256": source_sha,
        "output": str(args.output.resolve()),
        "output_sha256": sha256(args.output),
        "rows": rows,
        "episodes": int(len(np.unique(arrays["episode"]))),
        "option_contract": OPTION_IDS,
        "option_counts": {
            family: int(np.sum(option_ids == option)) for family, option in OPTION_IDS.items()
        },
        "unit_role_contract": {str(i): name for i, name in enumerate(UNIT_ROLE_NAMES)},
        "market_role_contract": {str(i): name for i, name in enumerate(MARKET_ROLE_NAMES)},
        "unit_active_role_counts": {
            UNIT_ROLE_NAMES[index]: int(unit_counts[index]) for index in range(len(UNIT_ROLE_NAMES))
        },
        "market_active_role_counts": {
            MARKET_ROLE_NAMES[index]: int(market_counts[index]) for index in range(len(MARKET_ROLE_NAMES))
        },
        "terminal_boundary": "official observation step >= 671 (last 48 decisions)",
        "strategy_parent": None,
        "inherits_v113_checkpoint": False,
        "source_checkpoint": None,
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
