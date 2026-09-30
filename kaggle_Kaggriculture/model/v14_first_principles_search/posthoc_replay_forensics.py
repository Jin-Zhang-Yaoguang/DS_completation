"""Post-hoc replay forensics for the already exposed V13C-vs-A2 results.

This script is deliberately not an evaluator and cannot choose a new seed.  It
only replays exact tasks already present in V13 confirmatory ``games.jsonl`` so
we can inspect trajectory-level cash, market, inventory, and action differences.
It never reads the frozen test split.
"""

from __future__ import annotations

import argparse
from collections import Counter
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

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
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
PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
    "FERTILIZER",
)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _market(action: Any) -> list[list[Any]]:
    if not isinstance(action, Mapping):
        return []
    value = action.get("market") or []
    return [list(row) for row in value if isinstance(row, (list, tuple))]


def _sell_totals(action: Any) -> Counter[str]:
    result: Counter[str] = Counter()
    for row in _market(action):
        if len(row) >= 3 and row[0] == "SELL":
            try:
                result[str(row[1])] += max(0, int(row[2]))
            except (TypeError, ValueError):
                continue
    return result


def _nonzero_inventory(private: Mapping[str, Any]) -> dict[str, Any]:
    shed = {
        str(key): int(value)
        for key, value in dict(private.get("shed") or {}).items()
        if int(value or 0) != 0
    }
    carried: Counter[str] = Counter()
    for inventory in list(private.get("inventories") or []):
        for key, value in dict(inventory or {}).items():
            carried[str(key)] += int(value or 0)
    return {
        "shed": shed,
        "carried": dict(carried),
        "seeds": {
            str(key): int(value)
            for key, value in dict(private.get("seeds") or {}).items()
            if int(value or 0) != 0
        },
    }


def _tile_counts(farm: Mapping[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in list(farm.get("tiles") or []):
        for tile in list(row or []):
            if not isinstance(tile, Mapping):
                continue
            animal = tile.get("animal")
            crop = tile.get("crop")
            kind = animal or crop or tile.get("kind")
            if kind:
                counts[str(kind)] += 1
    return dict(counts)


def _status(row: Mapping[str, Any], model: str) -> Mapping[str, Any]:
    return row["agent_diagnostics"][model]["underlying"]["model_status"]


def replay(task: Mapping[str, Any]) -> dict[str, Any]:
    registry = load_registry(task["registry"])
    raw_candidate = create_agent(registry, CANDIDATE)
    raw_anchor = create_agent(registry, ANCHOR)
    candidate_seat = int(task["model_a_seat"])
    agents = (
        [raw_candidate, raw_anchor]
        if candidate_seat == 0
        else [raw_anchor, raw_candidate]
    )
    seed = int(task["source"]["seed"])
    random.seed(seed * 104729 + candidate_seat * 1009)
    np.random.seed((seed + candidate_seat * 65537) % (2**32 - 1))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run(agents)

    statuses = [str(item.status) for item in env.state]
    rewards = [float(item.reward or 0.0) for item in env.state]
    if statuses != ["DONE", "DONE"] or rewards != [float(x) for x in task["rewards"]]:
        raise RuntimeError(
            f"replay mismatch {task['task_id']}: {statuses}/{rewards} != "
            f"{task['statuses']}/{task['rewards']}"
        )

    anchor_seat = 1 - candidate_seat
    action_difference_steps: list[int] = []
    market_difference_steps: list[int] = []
    first_market_difference: dict[str, Any] | None = None
    requested_sells = [Counter(), Counter()]
    requested_sells_by_day = [{}, {}]
    cash_spreads: list[float] = []

    # The state recorded at index 719 is DONE.  Step 718 is the last applied
    # action, so only steps 0..718 belong in action analysis.
    for step_index, states in enumerate(env.steps[:-1]):
        observations = [states[seat]["observation"] for seat in (0, 1)]
        actions = [states[seat]["action"] for seat in (0, 1)]
        if _plain(actions[candidate_seat]) != _plain(actions[anchor_seat]):
            action_difference_steps.append(step_index)
        candidate_market = _market(actions[candidate_seat])
        anchor_market = _market(actions[anchor_seat])
        if candidate_market != anchor_market:
            market_difference_steps.append(step_index)
            if first_market_difference is None:
                changed_products = sorted(
                    set(_sell_totals(actions[candidate_seat]))
                    | set(_sell_totals(actions[anchor_seat]))
                )
                common_market = observations[0]["market"]
                first_market_difference = {
                    "step": step_index,
                    "day": int(observations[0]["day"]),
                    "hour": int(observations[0]["hour"]),
                    "candidate_orders": candidate_market,
                    "anchor_orders": anchor_market,
                    "changed_products": changed_products,
                    "prices": {
                        item: float(common_market["prices"][item])
                        for item in changed_products
                        if item in common_market["prices"]
                    },
                    "market_inventory": {
                        item: int(common_market["inventory"][item])
                        for item in changed_products
                        if item in common_market["inventory"]
                    },
                }
        for seat in (0, 1):
            sold = _sell_totals(actions[seat])
            requested_sells[seat].update(sold)
            day = str(int(observations[seat]["day"]))
            day_counter = requested_sells_by_day[seat].setdefault(day, Counter())
            day_counter.update(sold)
        farms = observations[0]["farms"]
        cash_spreads.append(
            float(farms[candidate_seat]["money"])
            - float(farms[anchor_seat]["money"])
        )

    terminal = env.steps[-1]
    terminal_obs = [terminal[seat]["observation"] for seat in (0, 1)]
    common_market = terminal_obs[0]["market"]
    terminal_rows = []
    for seat in (candidate_seat, anchor_seat):
        private = terminal_obs[seat]["private"]
        farm = terminal_obs[seat]["farms"][seat]
        terminal_rows.append(
            {
                "seat": seat,
                "cash": float(farm["money"]),
                "inventory": _nonzero_inventory(private),
                "tile_counts": _tile_counts(farm),
                "unlocked_quadrants": list(farm.get("unlocked_quadrants") or []),
            }
        )

    original_candidate_status = _status(task, CANDIDATE)
    original_anchor_status = _status(task, ANCHOR)
    margin = rewards[candidate_seat] - rewards[anchor_seat]
    return {
        "task_id": task["task_id"],
        "source": task["source"],
        "candidate_seat": candidate_seat,
        "outcome": "W" if margin > 0 else "L" if margin < 0 else "T",
        "rewards": rewards,
        "margin": margin,
        "candidate_branch": original_candidate_status["parent_diagnostics"]["selected"],
        "anchor_branch": original_anchor_status["parent_diagnostics"]["selected"],
        "v8_wool_throttle_opportunities": int(
            original_candidate_status.get("v8_wool_throttle_opportunities") or 0
        ),
        "candidate_throttled_products": original_candidate_status.get(
            "throttled_product_steps", {}
        ),
        "anchor_throttled_products": original_anchor_status.get(
            "throttled_product_steps", {}
        ),
        "action_difference_count": len(action_difference_steps),
        "market_difference_count": len(market_difference_steps),
        "first_action_difference_step": (
            action_difference_steps[0] if action_difference_steps else None
        ),
        "first_market_difference": first_market_difference,
        "requested_sells": {
            "candidate": dict(requested_sells[candidate_seat]),
            "anchor": dict(requested_sells[anchor_seat]),
        },
        "requested_sells_by_day": {
            "candidate": {
                day: dict(counter)
                for day, counter in requested_sells_by_day[candidate_seat].items()
            },
            "anchor": {
                day: dict(counter)
                for day, counter in requested_sells_by_day[anchor_seat].items()
            },
        },
        "cash_spread": {
            "minimum": min(cash_spreads),
            "maximum": max(cash_spreads),
            "at_step_72": cash_spreads[72],
            "before_last_action": cash_spreads[-1],
            "terminal": margin,
        },
        "terminal": {
            "candidate": terminal_rows[0],
            "anchor": terminal_rows[1],
            "market_prices": {
                item: float(common_market["prices"][item]) for item in PRODUCTS
            },
            "market_inventory": {
                item: int(common_market["inventory"][item]) for item in PRODUCTS
            },
            "unlocked_shops": list(terminal_obs[0]["town"].get("unlocked_shops") or []),
        },
    }


def load_tasks(path: Path, registry: Path) -> list[dict[str, Any]]:
    tasks = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("model_a") != CANDIDATE or row.get("model_b") != ANCHOR:
                continue
            if row.get("source", {}).get("split") == "test":
                raise PermissionError("test row encountered; post-hoc forensics refuses it")
            if row.get("statuses") != ["DONE", "DONE"] or row.get("error") is not None:
                raise ValueError("input contains an invalid completed row")
            row["registry"] = str(registry.resolve())
            tasks.append(row)
    if len(tasks) != 200:
        raise ValueError(f"expected exactly 200 exposed A2 rows, got {len(tasks)}")
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=Path, default=DEFAULT_GAMES)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    tasks = load_tasks(args.games.resolve(), args.registry.resolve())
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = {pool.submit(replay, task): task["task_id"] for task in tasks}
        for index, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if index % 20 == 0:
                print(f"completed {index}/{len(tasks)}", flush=True)
    results.sort(
        key=lambda row: (
            row["source"]["date"],
            int(row["source"]["seed"]),
            int(row["candidate_seat"]),
        )
    )
    payload = {
        "schema": "kaggriculture-v14-posthoc-exposed-replay-forensics-1",
        "scope": "exact replay of already exposed V13 confirmatory A2 tasks only",
        "selection_use": "diagnostic only; not a validation panel",
        "test_access": False,
        "games_source": str(args.games.resolve()),
        "registry": str(args.registry.resolve()),
        "rows": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} ({len(results)} rows)", flush=True)


if __name__ == "__main__":
    main()
