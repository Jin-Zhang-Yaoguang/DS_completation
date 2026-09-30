"""Measure safe SELL-queue reorder coverage on exposed V13 TT/LL sources.

The input is restricted to exact, already exposed V13 confirmatory tasks.  This
is a post-hoc mechanism-coverage audit, not a performance panel.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import random
import sys
from typing import Any, Mapping

import numpy as np
from kaggle_environments import make

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (  # noqa: E402
    create_agent,
    load_registry,
)


DEFAULT_GAMES = Path(
    "kaggle_Kaggriculture/model/v13_dual_anchor_search/runs/confirmatory/"
    "v13c_a2_v8_no_wool_throttle/games.jsonl"
)
DEFAULT_REGISTRY = Path(
    "kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/"
    "clean_screen_registry.json"
)
CANDIDATE = "v13c_a2_v8_no_wool_throttle"
ANCHOR = "v12a2_no_shop_gate"
UNSAFE_UNIT_OPS = frozenset({"DROP", "PICKUP", "PLACE"})


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _market(action: Any) -> list[list[Any]]:
    if not isinstance(action, Mapping):
        return []
    return [
        list(row)
        for row in (action.get("market") or [])
        if isinstance(row, (list, tuple))
    ]


def _unit_ops(action: Any) -> set[str]:
    if not isinstance(action, Mapping):
        return set()
    rows = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    return {
        str(row[0])
        for row in rows
        if isinstance(row, (list, tuple)) and len(row) >= 1
    }


def _model_status(row: Mapping[str, Any], model: str) -> Mapping[str, Any]:
    return row["agent_diagnostics"][model]["underlying"]["model_status"]


def _source_key(row: Mapping[str, Any]) -> tuple[str, int, str]:
    source = row["source"]
    return str(source["date"]), int(source["seed"]), str(source["episode_id"])


def load_target_tasks(games: Path, registry: Path) -> list[dict[str, Any]]:
    rows = []
    with games.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("model_a") != CANDIDATE or row.get("model_b") != ANCHOR:
                continue
            if row.get("source", {}).get("split") == "test":
                raise PermissionError("test row encountered")
            rows.append(row)
    if len(rows) != 200:
        raise ValueError(f"expected 200 exposed C-vs-A2 rows, got {len(rows)}")

    by_source: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[_source_key(row)].append(row)
    target_patterns: dict[tuple[str, int, str], str] = {}
    for key, pair in by_source.items():
        if len(pair) != 2:
            raise ValueError(f"source does not have both seats: {key}")
        outcomes = []
        for row in sorted(pair, key=lambda item: int(item["model_a_seat"])):
            margin = float(row["margin_a"])
            outcomes.append("W" if margin > 0 else "L" if margin < 0 else "T")
        pattern = "".join(outcomes)
        if pattern in {"TT", "LL"}:
            target_patterns[key] = pattern
    if Counter(target_patterns.values()) != Counter({"TT": 27, "LL": 6}):
        raise ValueError(f"unexpected target pattern counts: {Counter(target_patterns.values())}")

    targets = []
    for row in rows:
        key = _source_key(row)
        if key not in target_patterns:
            continue
        candidate_status = _model_status(row, CANDIDATE)
        anchor_status = _model_status(row, ANCHOR)
        candidate_branch = candidate_status["parent_diagnostics"]["selected"]
        anchor_branch = anchor_status["parent_diagnostics"]["selected"]
        if candidate_branch != anchor_branch:
            raise ValueError(f"TT/LL row does not share branch: {row['task_id']}")
        task = dict(row)
        task["registry"] = str(registry.resolve())
        task["source_pattern"] = target_patterns[key]
        task["branch"] = candidate_branch
        targets.append(task)
    if len(targets) != 66:
        raise ValueError(f"expected 66 target rows, got {len(targets)}")
    return targets


def replay_coverage(task: Mapping[str, Any]) -> dict[str, Any]:
    registry = load_registry(task["registry"])
    candidate = create_agent(registry, CANDIDATE)
    anchor = create_agent(registry, ANCHOR)
    candidate_seat = int(task["model_a_seat"])
    agents = [candidate, anchor] if candidate_seat == 0 else [anchor, candidate]
    anchor_seat = 1 - candidate_seat
    seed = int(task["source"]["seed"])
    random.seed(seed * 104729 + candidate_seat * 1009)
    np.random.seed((seed + candidate_seat * 65537) % (2**32 - 1))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run(agents)
    statuses = [str(item.status) for item in env.state]
    rewards = [float(item.reward or 0.0) for item in env.state]
    if statuses != ["DONE", "DONE"] or rewards != [float(x) for x in task["rewards"]]:
        raise RuntimeError(f"exact replay mismatch: {task['task_id']}")

    opportunities = []
    for step, states in enumerate(env.steps[:-1]):
        actions = [states[seat]["action"] for seat in (0, 1)]
        candidate_action = actions[candidate_seat]
        anchor_action = actions[anchor_seat]
        candidate_queue = _market(candidate_action)
        anchor_queue = _market(anchor_action)
        if _plain(candidate_queue) != _plain(anchor_queue):
            continue
        if len(candidate_queue) < 2:
            continue
        if not all(len(row) >= 3 and str(row[0]) == "SELL" for row in candidate_queue):
            continue
        candidate_unsafe = bool(_unit_ops(candidate_action) & UNSAFE_UNIT_OPS)
        anchor_unsafe = bool(_unit_ops(anchor_action) & UNSAFE_UNIT_OPS)
        if candidate_unsafe:
            continue
        obs = states[candidate_seat]["observation"]
        products = [str(row[1]) for row in candidate_queue]
        prices = {
            product: float(obs["market"]["prices"].get(product, 0.0))
            for product in sorted(set(products))
        }
        strict_safe = not anchor_unsafe
        opportunities.append(
            {
                "step": step,
                "day": int(obs["day"]),
                "hour": int(obs["hour"]),
                "sell_slots": len(candidate_queue),
                "distinct_products": len(set(products)),
                "products": products,
                "quantities": [int(row[2]) for row in candidate_queue],
                "prices": prices,
                "strict_both_sides_no_deposit_or_pickup": strict_safe,
                "economically_active": (
                    len(set(products)) >= 2
                    and any(price > 1.0 for price in prices.values())
                ),
            }
        )

    strict = [
        row
        for row in opportunities
        if row["strict_both_sides_no_deposit_or_pickup"]
    ]
    economic = [row for row in strict if row["economically_active"]]
    strict_slot_histogram = Counter(str(row["sell_slots"]) for row in strict)
    economic_slot_histogram = Counter(str(row["sell_slots"]) for row in economic)
    economic_distinct_histogram = Counter(
        str(row["distinct_products"]) for row in economic
    )
    economic_product_slots: Counter[str] = Counter()
    for row in economic:
        economic_product_slots.update(row["products"])
    return {
        "task_id": task["task_id"],
        "source": task["source"],
        "source_pattern": task["source_pattern"],
        "candidate_seat": candidate_seat,
        "branch": task["branch"],
        "candidate_safe_opportunity_steps": len(opportunities),
        "strict_safe_opportunity_steps": len(strict),
        "economic_strict_opportunity_steps": len(economic),
        "strict_safe_sell_slots": sum(row["sell_slots"] for row in strict),
        "economic_strict_sell_slots": sum(row["sell_slots"] for row in economic),
        "strict_safe_slot_histogram": dict(strict_slot_histogram),
        "economic_strict_slot_histogram": dict(economic_slot_histogram),
        "economic_distinct_product_histogram": dict(economic_distinct_histogram),
        "economic_product_slots": dict(economic_product_slots),
        "strict_safe_examples": strict[:5],
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[_source_key(row)].append(row)

    def source_coverage(pattern: str, field: str, both: bool = False) -> dict[str, int]:
        groups = [
            pair
            for pair in by_source.values()
            if pair[0]["source_pattern"] == pattern
        ]
        covered = sum(
            (all(int(row[field]) > 0 for row in pair) if both else any(int(row[field]) > 0 for row in pair))
            for pair in groups
        )
        return {"covered": covered, "total": len(groups)}

    def sum_counter(subset: list[dict[str, Any]], field: str) -> dict[str, int]:
        total: Counter[str] = Counter()
        for row in subset:
            total.update({str(key): int(value) for key, value in row[field].items()})
        return dict(sorted(total.items(), key=lambda item: item[0]))

    result: dict[str, Any] = {
        "row_count": len(rows),
        "source_count": len(by_source),
        "by_pattern": {},
        "by_branch": {},
    }
    for pattern in ("TT", "LL"):
        subset = [row for row in rows if row["source_pattern"] == pattern]
        result["by_pattern"][pattern] = {
            "rows": len(subset),
            "sources": len(subset) // 2,
            "strict_steps": sum(row["strict_safe_opportunity_steps"] for row in subset),
            "strict_sell_slots": sum(row["strict_safe_sell_slots"] for row in subset),
            "economic_steps": sum(row["economic_strict_opportunity_steps"] for row in subset),
            "economic_sell_slots": sum(row["economic_strict_sell_slots"] for row in subset),
            "strict_slot_histogram": sum_counter(
                subset, "strict_safe_slot_histogram"
            ),
            "economic_slot_histogram": sum_counter(
                subset, "economic_strict_slot_histogram"
            ),
            "economic_distinct_product_histogram": sum_counter(
                subset, "economic_distinct_product_histogram"
            ),
            "economic_product_slots": sum_counter(
                subset, "economic_product_slots"
            ),
            "source_any_strict": source_coverage(pattern, "strict_safe_opportunity_steps"),
            "source_both_seats_strict": source_coverage(
                pattern, "strict_safe_opportunity_steps", both=True
            ),
            "source_any_economic": source_coverage(
                pattern, "economic_strict_opportunity_steps"
            ),
            "source_both_seats_economic": source_coverage(
                pattern, "economic_strict_opportunity_steps", both=True
            ),
        }
    for branch in sorted({str(row["branch"]) for row in rows}):
        subset = [row for row in rows if row["branch"] == branch]
        result["by_branch"][branch] = {
            "rows": len(subset),
            "strict_steps": sum(row["strict_safe_opportunity_steps"] for row in subset),
            "economic_steps": sum(row["economic_strict_opportunity_steps"] for row in subset),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, default=DEFAULT_GAMES)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    tasks = load_target_tasks(args.games.resolve(), args.registry.resolve())
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = {pool.submit(replay_coverage, task): task["task_id"] for task in tasks}
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 10 == 0:
                print(f"completed {index}/{len(tasks)}", flush=True)
    rows.sort(
        key=lambda row: (
            row["source"]["date"],
            int(row["source"]["seed"]),
            int(row["candidate_seat"]),
        )
    )
    payload = {
        "schema": "kaggriculture-v14-posthoc-queue-coverage-1",
        "scope": "exact replay of exposed V13 TT/LL tasks only",
        "selection_use": "diagnostic only; not a validation panel",
        "test_access": False,
        "summary": summarise(rows),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} ({len(rows)} rows)", flush=True)


if __name__ == "__main__":
    main()
