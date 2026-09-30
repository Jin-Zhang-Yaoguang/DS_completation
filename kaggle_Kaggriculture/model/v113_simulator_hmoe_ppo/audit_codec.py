"""Audit V113 action vocabulary and state-conditioned round-trip coverage."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import time

import action_space as space
import engine_parity


def _op_target(order):
    if not isinstance(order, list) or not order:
        return ("PASS", None)
    return (str(order[0]), str(order[1]) if len(order) >= 2 else None)


def _action_op_targets(action):
    return {
        "farmer": _op_target(action["farmer"]),
        "hands": [_op_target(order) for order in action["hands"]],
        "market": [_op_target(order) for order in action["market"]],
    }


def _schema_valid(action, expected_hands):
    if not isinstance(action, dict) or set(action) != {"farmer", "hands", "market"}:
        return False
    if not isinstance(action["farmer"], list) or not action["farmer"]:
        return False
    if not isinstance(action["hands"], list) or len(action["hands"]) != expected_hands:
        return False
    if not isinstance(action["market"], list) or len(action["market"]) > space.MAX_MARKET_SLOTS:
        return False
    return all(isinstance(order, list) and order for order in [action["farmer"], *action["hands"], *action["market"]])


def audit(files: list[Path]) -> dict:
    started = time.time()
    totals = Counter()
    expert_counts = Counter()
    unknown_examples = []
    for path in files:
        replay = json.loads(path.read_text(encoding="utf-8"))
        steps = replay.get("steps") or []
        for action_index in range(1, len(steps)):
            for seat in (0, 1):
                obs = dict(steps[action_index - 1][seat].get("observation") or {})
                obs["step"] = action_index - 1
                source = space.normalise_action(steps[action_index][seat].get("action") or {}, space.unit_count(obs) - 1)
                encoded = space.encode_action(obs, source)
                decoded = space.decode_action(obs, encoded)
                closed = space.decode_action(obs, space.encode_action(obs, decoded))
                totals["actions"] += 1
                totals["unit_orders"] += len(encoded["unit_known"])
                totals["known_unit_orders"] += sum(encoded["unit_known"])
                source_market_count = len(source["market"])
                totals["market_orders"] += source_market_count
                totals["known_market_orders"] += sum(encoded["market_known"][:source_market_count])
                if _action_op_targets(source) == _action_op_targets(decoded):
                    totals["op_target_roundtrip"] += 1
                else:
                    totals["op_target_mismatch"] += 1
                    if len(unknown_examples) < 20:
                        unknown_examples.append({"episode": int(path.stem), "step": action_index - 1, "seat": seat, "source": source, "decoded": decoded})
                if source == decoded:
                    totals["raw_exact_roundtrip"] += 1
                else:
                    totals["cleaned_source_actions"] += 1
                if decoded == closed:
                    totals["executable_action_closure"] += 1
                if _schema_valid(decoded, space.unit_count(obs) - 1):
                    totals["decoded_schema_valid"] += 1
                expert_counts[space.functional_expert_label(source, action_index - 1)] += 1
    unit_coverage = totals["known_unit_orders"] / max(1, totals["unit_orders"])
    market_coverage = totals["known_market_orders"] / max(1, totals["market_orders"])
    op_target_coverage = totals["op_target_roundtrip"] / max(1, totals["actions"])
    action_closure = totals["executable_action_closure"] / max(1, totals["actions"])
    schema_valid = totals["decoded_schema_valid"] / max(1, totals["actions"])
    return {
        "schema": "kaggriculture-v113-codec-audit-v1",
        "model_id": "v113_simulator_hmoe_ppo",
        "gate": "CODEC_AUDIT",
        "files": len(files),
        "episodes": [int(path.stem) for path in files],
        "totals": dict(totals),
        "unit_vocabulary_coverage": unit_coverage,
        "market_vocabulary_coverage": market_coverage,
        "action_op_target_roundtrip": op_target_coverage,
        "raw_exact_roundtrip": totals["raw_exact_roundtrip"] / max(1, totals["actions"]),
        "source_action_cleaning_rate": totals["cleaned_source_actions"] / max(1, totals["actions"]),
        "executable_action_closure": action_closure,
        "decoded_schema_valid": schema_valid,
        "expert_initialization_counts": {str(key): value for key, value in sorted(expert_counts.items())},
        "gate_thresholds": {"unit_vocabulary": 0.999, "market_vocabulary": 0.999, "executable_action_closure": 1.0, "decoded_schema_valid": 1.0},
        "gate_passed": unit_coverage >= 0.999 and market_coverage >= 0.999 and action_closure == 1.0 and schema_valid == 1.0,
        "examples": unknown_examples,
        "elapsed_seconds": time.time() - started,
    }


def atomic_json(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(report, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--module-version", default="1.32.7")
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--selection-seed", type=int, default=113002)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = engine_parity.discover(args.episodes_root, args.module_version)
    selected = engine_parity.select_samples(rows, args.samples, args.selection_seed)
    report = audit([Path(row["path"]) for row in selected])
    atomic_json(args.output, report)
    print(json.dumps({key: report[key] for key in ("files", "unit_vocabulary_coverage", "market_vocabulary_coverage", "action_op_target_roundtrip", "raw_exact_roundtrip", "source_action_cleaning_rate", "executable_action_closure", "decoded_schema_valid", "gate_passed")}, ensure_ascii=False, indent=2))
    if not report["gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
