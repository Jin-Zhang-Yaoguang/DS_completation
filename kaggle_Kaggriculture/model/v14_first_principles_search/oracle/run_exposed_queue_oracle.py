"""Oracle ceiling for queue reordering on the already-exposed V13 confirm panel.

This is diagnostic code, not a submission candidate.  At every turn it sees
both agents' actual actions and both private observations, then evaluates every
permutation of the candidate's existing all-SELL queue by stepping a deep copy
of the official environment.  Only the chosen permutation is applied to the
live closed-loop game.  Farmer/hand actions, SELL quantities and market slots
are unchanged.

Two modes are supported:

* strict: both queues are all-SELL and neither side transfers shed inventory
  with a worker on that turn.  This is the closest oracle counterpart to the
  current prototype's intended SELL-only simulator.
* broad: only the candidate queue must be all-SELL.  Official one-step clones
  account for a mixed opponent queue and all worker-side effects.  This is a
  wider, still action-compliant, myopic market-interference ceiling.

The panel was consumed by V13 before this script existed.  Do not point this
script at a new screen, confirmatory or test panel.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

V10 = WORKSPACE / "kaggle_Kaggriculture/model/v10_replay_lolo_router"
if str(V10) not in sys.path:
    sys.path.insert(0, str(V10))

from agent_factory import create_agent, load_registry  # noqa: E402
from kaggle_Kaggriculture.model.v14_first_principles_search.prototype_queue_solver import (  # noqa: E402
    _simulate_sell_queues,
)


CANDIDATE = "v13c_a2_v8_no_wool_throttle"
OPPONENT = "v12a2_no_shop_gate"
SELL_PRODUCTS = {
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
}
TRANSFER_ACTIONS = {"DROP", "PICKUP", "PLACE"}


def _canonical_action(action: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    source = copy.deepcopy(dict(action or {}))
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(item or ["PASS"]) for item in source.get("hands", [])],
        "market": [list(item) for item in source.get("market", [])],
    }


def _parse_sell(order: Sequence[Any] | None) -> tuple[str, int] | None:
    if not order or len(order) < 3 or str(order[0]) != "SELL":
        return None
    item = str(order[1])
    if item not in SELL_PRODUCTS:
        return None
    try:
        quantity = max(0, int(order[2]))
    except (TypeError, ValueError):
        return None
    return (item, quantity) if quantity else None


def _all_sell(action: Mapping[str, Any]) -> bool:
    market = action.get("market") or []
    return bool(market) and all(_parse_sell(order) is not None for order in market)


def _has_transfer(action: Mapping[str, Any]) -> bool:
    worker_orders = [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]
    return any(order and str(order[0]) in TRANSFER_ACTIONS for order in worker_orders)


def _money(env: Any, seat: int) -> float:
    state = env.state[seat]
    obs = state.observation
    farms = obs.get("farms", [])
    if farms and len(farms) == 2:
        return float(farms[seat].get("money", 0.0) or 0.0)
    return float(state.reward or 0.0)


def _outcome(margin: float) -> str:
    return "W" if margin > 0 else "T" if margin == 0 else "L"


def _branch(agent: Any) -> str | None:
    method = getattr(agent, "diagnostics", None)
    payload = dict(method()) if callable(method) else {}

    def visit(value: Any) -> str | None:
        if isinstance(value, Mapping):
            selected = value.get("selected")
            if isinstance(selected, str) and selected.startswith("baseline_"):
                return selected
            for key in (
                "parent_diagnostics", "model_status", "underlying", "router",
                "parent", "diagnostics",
            ):
                if key in value:
                    found = visit(value[key])
                    if found:
                        return found
            for child in value.values():
                found = visit(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = visit(child)
                if found:
                    return found
        return None

    return visit(payload)


def _private_shed(obs: Any) -> dict[str, int]:
    private = obs.get("private", {}) or {}
    shed = private.get("shed", {}) or {}
    return {str(key): int(value or 0) for key, value in dict(shed).items()}


def _eligible_permutations(action: Mapping[str, Any], max_orders: int) -> list[list[list[Any]]]:
    market = action.get("market") or []
    if not _all_sell(action) or len(market) < 2 or len(market) > int(max_orders):
        return []
    if len({str(order[1]) for order in market}) < 2:
        return []
    baseline = tuple(tuple(value) for value in market)
    unique = {
        tuple(tuple(value) for value in permutation)
        for permutation in itertools.permutations(market)
    }
    unique.discard(baseline)
    return [
        [list(order) for order in permutation]
        for permutation in sorted(unique, key=lambda rows: tuple(str(v) for row in rows for v in row))
    ]


def _step_clone(env: Any, actions: list[dict[str, list[Any]]]) -> tuple[float, float, list[str]]:
    branch = copy.deepcopy(env)
    branch.step(actions)
    monies = (_money(branch, 0), _money(branch, 1))
    statuses = [str(state.status) for state in branch.state]
    return monies[0], monies[1], statuses


def _oracle_action(
    env: Any,
    candidate_seat: int,
    candidate_action: dict[str, list[Any]],
    opponent_action: dict[str, list[Any]],
    mode: str,
    max_orders: int,
) -> tuple[dict[str, list[Any]], dict[str, Any]]:
    opponent_seat = 1 - candidate_seat
    baseline_actions = [candidate_action, opponent_action] if candidate_seat == 0 else [opponent_action, candidate_action]
    diagnostic: dict[str, Any] = {
        "eligible": False,
        "triggered": False,
        "permutations": 0,
        "relative_cash_gain": 0.0,
        "own_cash_gain": 0.0,
        "baseline_queue": copy.deepcopy(candidate_action["market"]),
        "opponent_queue": copy.deepcopy(opponent_action["market"]),
    }
    if not _all_sell(candidate_action):
        diagnostic["skip"] = "candidate_not_all_sell"
        return candidate_action, diagnostic
    if mode == "strict" and (not _all_sell(opponent_action) or _has_transfer(candidate_action) or _has_transfer(opponent_action)):
        diagnostic["skip"] = "strict_opponent_or_transfer_gate"
        return candidate_action, diagnostic
    permutations = _eligible_permutations(candidate_action, max_orders)
    if not permutations:
        diagnostic["skip"] = "no_distinct_permutation"
        return candidate_action, diagnostic

    diagnostic["eligible"] = True
    diagnostic["permutations"] = len(permutations)
    if mode == "strict":
        candidate_obs = env.state[candidate_seat].observation
        opponent_obs = env.state[opponent_seat].observation
        inventory = {
            str(key): int(value or 0)
            for key, value in dict(candidate_obs.get("market", {}).get("inventory", {})).items()
        }
        candidate_shed = _private_shed(candidate_obs)
        opponent_shed = _private_shed(opponent_obs)
        base_own, base_opp = _simulate_sell_queues(
            candidate_action["market"],
            opponent_action["market"],
            inventory,
            candidate_shed,
            opponent_shed,
        )
        best_action = candidate_action
        best_own, best_opp = base_own, base_opp
        best_objective = base_own - base_opp
        best_key = tuple(str(order[1]) for order in candidate_action["market"])
        for market in permutations:
            own, opp = _simulate_sell_queues(
                market,
                opponent_action["market"],
                inventory,
                candidate_shed,
                opponent_shed,
            )
            objective = own - opp
            key = tuple(str(order[1]) for order in market)
            if own + 1e-9 < base_own:
                continue
            if (
                objective > best_objective + 1e-9
                or (
                    abs(objective - best_objective) <= 1e-9
                    and (own > best_own + 1e-9 or (abs(own - best_own) <= 1e-9 and key < best_key))
                )
            ):
                best_action = copy.deepcopy(candidate_action)
                best_action["market"] = market
                best_own, best_opp = own, opp
                best_objective = objective
                best_key = key
        diagnostic["relative_cash_gain"] = float(best_objective - (base_own - base_opp))
        diagnostic["own_cash_gain"] = float(best_own - base_own)
        diagnostic["triggered"] = best_action != candidate_action and diagnostic["relative_cash_gain"] > 0
        diagnostic["chosen_queue"] = copy.deepcopy(best_action["market"])
        return best_action, diagnostic

    base_money = _step_clone(env, baseline_actions)[:2]
    base_own = base_money[candidate_seat]
    base_opp = base_money[opponent_seat]
    best_action = candidate_action
    best_money = base_money
    best_objective = base_own - base_opp
    best_key = tuple(str(order[1]) for order in candidate_action["market"])
    for market in permutations:
        trial_action = copy.deepcopy(candidate_action)
        trial_action["market"] = market
        actions = [trial_action, opponent_action] if candidate_seat == 0 else [opponent_action, trial_action]
        trial_money = _step_clone(env, actions)[:2]
        own = trial_money[candidate_seat]
        opp = trial_money[opponent_seat]
        objective = own - opp
        key = tuple(str(order[1]) for order in market)
        # Match the prototype's liquidity guard.  Among equal relative gains,
        # prefer own cash and then a deterministic product order.
        if own + 1e-9 < base_own:
            continue
        if (
            objective > best_objective + 1e-9
            or (
                abs(objective - best_objective) <= 1e-9
                and (own > best_money[candidate_seat] + 1e-9 or (abs(own - best_money[candidate_seat]) <= 1e-9 and key < best_key))
            )
        ):
            best_action = trial_action
            best_money = trial_money
            best_objective = objective
            best_key = key
    diagnostic["relative_cash_gain"] = float(best_objective - (base_own - base_opp))
    diagnostic["own_cash_gain"] = float(best_money[candidate_seat] - base_own)
    diagnostic["triggered"] = best_action != candidate_action and diagnostic["relative_cash_gain"] > 0
    diagnostic["chosen_queue"] = copy.deepcopy(best_action["market"])
    return best_action, diagnostic


def _run_game(task: Mapping[str, Any]) -> dict[str, Any]:
    from kaggle_environments import make

    started = time.perf_counter()
    registry = load_registry(task["registry"])
    candidate_id = str(task.get("candidate") or CANDIDATE)
    opponent_id = str(task.get("opponent") or OPPONENT)
    candidate = create_agent(registry, candidate_id)
    opponent = create_agent(registry, opponent_id)
    seat = int(task["candidate_seat"])
    seed = int(task["source"]["seed"])
    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.reset(2)
    events: list[dict[str, Any]] = []
    eligible_steps = 0
    triggered_steps = 0
    relative_gain = 0.0
    own_gain = 0.0
    step = 0
    while [str(state.status) for state in env.state] == ["ACTIVE", "ACTIVE"]:
        for state in env.state:
            state.observation.step = step
        candidate_obs = env.state[seat].observation
        opponent_obs = env.state[1 - seat].observation
        candidate_action = _canonical_action(candidate(candidate_obs, env.configuration))
        opponent_action = _canonical_action(opponent(opponent_obs, env.configuration))
        if bool(task.get("oracle_enabled", True)):
            chosen, diag = _oracle_action(
                env,
                seat,
                candidate_action,
                opponent_action,
                str(task["mode"]),
                int(task["max_orders"]),
            )
        else:
            chosen = candidate_action
            diag = {
                "eligible": False,
                "triggered": False,
                "permutations": 0,
                "relative_cash_gain": 0.0,
                "own_cash_gain": 0.0,
            }
        if diag["eligible"]:
            eligible_steps += 1
        if diag["triggered"]:
            triggered_steps += 1
            relative_gain += float(diag["relative_cash_gain"])
            own_gain += float(diag["own_cash_gain"])
            if bool(task.get("verify_official")):
                baseline_actions = [candidate_action, opponent_action] if seat == 0 else [opponent_action, candidate_action]
                chosen_actions = [chosen, opponent_action] if seat == 0 else [opponent_action, chosen]
                baseline_money = _step_clone(env, baseline_actions)[:2]
                chosen_money = _step_clone(env, chosen_actions)[:2]
                other = 1 - seat
                official_own_gain = chosen_money[seat] - baseline_money[seat]
                official_relative_gain = (
                    chosen_money[seat] - chosen_money[other]
                    - (baseline_money[seat] - baseline_money[other])
                )
                diag["official_own_cash_gain"] = float(official_own_gain)
                diag["official_relative_cash_gain"] = float(official_relative_gain)
                diag["official_match"] = (
                    abs(official_own_gain - float(diag["own_cash_gain"])) <= 1e-9
                    and abs(official_relative_gain - float(diag["relative_cash_gain"])) <= 1e-9
                )
                if not diag["official_match"]:
                    raise AssertionError(
                        "SELL simulator disagrees with official one-step counterfactual: "
                        f"predicted=({diag['own_cash_gain']},{diag['relative_cash_gain']}) "
                        f"official=({official_own_gain},{official_relative_gain})"
                    )
            diag.update({
                "step": step,
                "day": int(candidate_obs.get("day", 0) or 0),
                "hour": int(candidate_obs.get("hour", 0) or 0),
                "candidate_shed": _private_shed(candidate_obs),
                "opponent_shed": _private_shed(opponent_obs),
            })
            events.append(diag)
        actions = [chosen, opponent_action] if seat == 0 else [opponent_action, chosen]
        env.step(actions)
        step += 1
        if step > 1000:
            raise RuntimeError("environment exceeded 1000 steps")
    statuses = [str(state.status) for state in env.state]
    rewards = [float(state.reward or 0.0) for state in env.state]
    margin = rewards[seat] - rewards[1 - seat]
    return {
        "schema": "kaggriculture-v14-exposed-queue-oracle-game-1",
        "mode": str(task["mode"]),
        "candidate": candidate_id,
        "opponent": opponent_id,
        "candidate_seat": seat,
        "source": dict(task["source"]),
        "statuses": statuses,
        "rewards": rewards,
        "candidate_reward": rewards[seat],
        "opponent_reward": rewards[1 - seat],
        "margin": margin,
        "outcome": _outcome(margin),
        "candidate_branch": _branch(candidate),
        "opponent_branch": _branch(opponent),
        "eligible_steps": eligible_steps,
        "triggered_steps": triggered_steps,
        "oracle_relative_cash_gain": relative_gain,
        "oracle_own_cash_gain": own_gain,
        "events": events,
        "official_event_checks": sum(bool(event.get("official_match")) for event in events),
        "closed_loop": True,
        "actual_opponent_action_visible": True,
        "official_engine_counterfactual": True,
        "elapsed_seconds": time.perf_counter() - started,
    }


def _baseline_rows(path: Path) -> dict[tuple[int, int], dict[str, Any]]:
    rows = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("model_a") != CANDIDATE or row.get("model_b") != OPPONENT:
                continue
            key = (int(row["source"]["seed"]), int(row["model_a_seat"]))
            rows[key] = row
    if len(rows) != 200:
        raise ValueError(f"expected 200 exposed baseline games, found {len(rows)}")
    return rows


def _source_pattern(rows: Sequence[Mapping[str, Any]], outcome_key: str) -> dict[int, str]:
    grouped: dict[int, dict[int, str]] = defaultdict(dict)
    for row in rows:
        grouped[int(row["source"]["seed"])][int(row["candidate_seat"])] = str(row[outcome_key])
    return {seed: "".join(by_seat.get(seat, "?") for seat in (0, 1)) for seed, by_seat in grouped.items()}


def _summarise(rows: list[dict[str, Any]], baseline: dict[tuple[int, int], dict[str, Any]], mode: str) -> dict[str, Any]:
    transitions = Counter()
    by_date: dict[str, Counter[str]] = defaultdict(Counter)
    by_seat: dict[str, Counter[str]] = defaultdict(Counter)
    by_branch: dict[str, Counter[str]] = defaultdict(Counter)
    baseline_for_patterns = []
    for row in rows:
        key = (int(row["source"]["seed"]), int(row["candidate_seat"]))
        old = baseline[key]
        old_outcome = _outcome(float(old["margin_a"]))
        new_outcome = str(row["outcome"])
        row["baseline_margin"] = float(old["margin_a"])
        row["baseline_outcome"] = old_outcome
        transitions[f"{old_outcome}->{new_outcome}"] += 1
        date = str(row["source"]["date"])
        seat = str(row["candidate_seat"])
        branch = f"{row.get('candidate_branch') or 'unknown'}/{row.get('opponent_branch') or 'unknown'}"
        by_date[date][new_outcome] += 1
        by_seat[seat][new_outcome] += 1
        by_branch[branch][new_outcome] += 1
        baseline_for_patterns.append({
            "source": row["source"], "candidate_seat": row["candidate_seat"], "outcome": old_outcome,
        })
    old_patterns = _source_pattern(baseline_for_patterns, "outcome")
    new_patterns = _source_pattern(rows, "outcome")
    pattern_transitions = Counter(f"{old_patterns[seed]}->{new_patterns[seed]}" for seed in sorted(new_patterns))
    outcomes = Counter(str(row["outcome"]) for row in rows)
    games_with_trigger = sum(int(row["triggered_steps"]) > 0 for row in rows)
    sources_with_trigger = len({int(row["source"]["seed"]) for row in rows if int(row["triggered_steps"]) > 0})
    return {
        "schema": "kaggriculture-v14-exposed-queue-oracle-summary-1",
        "mode": mode,
        "epistemic_status": "oracle ceiling on previously exposed V13 confirmatory sources; not validation",
        "candidate_parent": CANDIDATE,
        "opponent": OPPONENT,
        "games": len(rows),
        "sources": len({int(row["source"]["seed"]) for row in rows}),
        "outcomes": dict(outcomes),
        "pure_win_rate": outcomes["W"] / len(rows),
        "score_rate": (outcomes["W"] + 0.5 * outcomes["T"]) / len(rows),
        "baseline_to_oracle_transitions": dict(sorted(transitions.items())),
        "paired_source_pattern_transitions": dict(sorted(pattern_transitions.items())),
        "games_with_trigger": games_with_trigger,
        "game_trigger_coverage": games_with_trigger / len(rows),
        "sources_with_trigger": sources_with_trigger,
        "source_trigger_coverage": sources_with_trigger / len(new_patterns),
        "eligible_steps": sum(int(row["eligible_steps"]) for row in rows),
        "triggered_steps": sum(int(row["triggered_steps"]) for row in rows),
        "oracle_relative_cash_gain": sum(float(row["oracle_relative_cash_gain"]) for row in rows),
        "oracle_own_cash_gain": sum(float(row["oracle_own_cash_gain"]) for row in rows),
        "by_date": {key: dict(value) for key, value in sorted(by_date.items())},
        "by_seat": {key: dict(value) for key, value in sorted(by_seat.items())},
        "by_branch_pair": {key: dict(value) for key, value in sorted(by_branch.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("strict", "broad"), required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--max-orders", type=int, default=7)
    parser.add_argument(
        "--registry",
        type=Path,
        default=WORKSPACE / "kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/clean_screen_registry.json",
    )
    parser.add_argument(
        "--baseline-games",
        type=Path,
        default=WORKSPACE / "kaggle_Kaggriculture/model/v13_dual_anchor_search/runs/confirmatory/v13c_a2_v8_no_wool_throttle/games.jsonl",
    )
    parser.add_argument("--output-dir", type=Path, default=HERE)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--verify-official", action="store_true")
    args = parser.parse_args()

    baseline = _baseline_rows(args.baseline_games.resolve())
    source_by_seed = {}
    for row in baseline.values():
        source_by_seed[int(row["source"]["seed"])] = dict(row["source"])
    tasks = [
        {
            "registry": str(args.registry.resolve()),
            "source": source_by_seed[seed],
            "candidate_seat": seat,
            "mode": args.mode,
            "max_orders": int(args.max_orders),
            "verify_official": bool(args.verify_official),
        }
        for seed in sorted(source_by_seed)
        for seat in (0, 1)
    ]
    if args.limit:
        tasks = tasks[: int(args.limit)]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / f"{args.mode}_games.jsonl"
    summary_path = args.output_dir / f"{args.mode}_summary.json"
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = {pool.submit(_run_game, task): task for task in tasks}
        for index, future in enumerate(as_completed(futures), 1):
            row = future.result()
            rows.append(row)
            if index % 20 == 0 or index == len(futures):
                print(f"[{args.mode}] {index}/{len(futures)}", flush=True)
    rows.sort(key=lambda row: (int(row["source"]["seed"]), int(row["candidate_seat"])))
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    if len(rows) == 200:
        summary = _summarise(rows, baseline, args.mode)
    else:
        summary = {
            "schema": "kaggriculture-v14-exposed-queue-oracle-smoke-1",
            "mode": args.mode,
            "games": len(rows),
            "rows_sha256": hashlib.sha256(jsonl_path.read_bytes()).hexdigest(),
        }
    summary["games_file"] = str(jsonl_path.resolve())
    summary["games_sha256"] = hashlib.sha256(jsonl_path.read_bytes()).hexdigest()
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
