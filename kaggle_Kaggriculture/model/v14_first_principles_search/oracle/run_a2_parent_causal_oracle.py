"""Isolate the queue residual with A2 as both parent and opponent.

Uses only the already-consumed V13 screen panel (36 sources x both seats).
Runs an unmodified A2-vs-A2 baseline and an A2+true-action strict queue oracle
against A2.  This is causal mechanism diagnosis, not unseen validation.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from run_exposed_queue_oracle import _outcome, _run_game


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
A2 = "v12a2_no_shop_gate"


def _run_tasks(tasks: list[dict[str, Any]], workers: int, label: str) -> list[dict[str, Any]]:
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, int(workers))) as pool:
        futures = [pool.submit(_run_game, task) for task in tasks]
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 12 == 0 or index == len(futures):
                print(f"[{label}] {index}/{len(futures)}", flush=True)
    return sorted(rows, key=lambda row: (int(row["source"]["seed"]), int(row["candidate_seat"])))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paired_patterns(rows: list[Mapping[str, Any]]) -> dict[int, str]:
    grouped: dict[int, dict[int, str]] = defaultdict(dict)
    for row in rows:
        grouped[int(row["source"]["seed"])][int(row["candidate_seat"])] = str(row["outcome"])
    return {seed: "".join(by_seat[seat] for seat in (0, 1)) for seed, by_seat in grouped.items()}


def _group_outcomes(rows: list[Mapping[str, Any]], key_fn: Any) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(key_fn(row))].append(row)
    result = {}
    for key, values in sorted(grouped.items()):
        counts = Counter(str(row["outcome"]) for row in values)
        result[key] = {
            "games": len(values),
            "W": counts["W"],
            "T": counts["T"],
            "L": counts["L"],
            "pure_win_rate": counts["W"] / len(values),
            "games_with_trigger": sum(int(row["triggered_steps"]) > 0 for row in values),
            "triggered_steps": sum(int(row["triggered_steps"]) for row in values),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--max-orders", type=int, default=7)
    parser.add_argument(
        "--registry",
        type=Path,
        default=WORKSPACE / "kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/clean_screen_registry.json",
    )
    parser.add_argument(
        "--panel",
        type=Path,
        default=WORKSPACE / "kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/screen_panel.json",
    )
    parser.add_argument(
        "--exposure-evidence",
        type=Path,
        default=WORKSPACE / "kaggle_Kaggriculture/model/v13_dual_anchor_search/runs/screen/v13c_a2_v8_no_wool_throttle/games.jsonl",
    )
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()

    panel = json.loads(args.panel.read_text(encoding="utf-8"))
    records = list(panel.get("records") or [])
    if len(records) != 36 or not args.exposure_evidence.is_file():
        raise ValueError("refusing: expected the already-consumed 36-source V13 screen panel")
    exposed_seeds = {
        int(json.loads(line)["source"]["seed"])
        for line in args.exposure_evidence.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    panel_seeds = {int(row["seed"]) for row in records}
    if not panel_seeds.issubset(exposed_seeds):
        raise ValueError("refusing: exposure evidence does not cover the entire panel")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    common = [
        {
            "registry": str(args.registry.resolve()),
            "source": dict(source),
            "candidate_seat": seat,
            "candidate": A2,
            "opponent": A2,
            "mode": "strict",
            "max_orders": int(args.max_orders),
        }
        for source in records
        for seat in (0, 1)
    ]
    baseline_tasks = [{**task, "oracle_enabled": False} for task in common]
    oracle_tasks = [{**task, "oracle_enabled": True} for task in common]
    baseline = _run_tasks(baseline_tasks, args.workers, "a2-baseline")
    oracle = _run_tasks(oracle_tasks, args.workers, "a2-oracle")
    baseline_path = args.output_dir / "a2_parent_baseline_games.jsonl"
    oracle_path = args.output_dir / "a2_parent_oracle_games.jsonl"
    baseline_sha = _write_jsonl(baseline_path, baseline)
    oracle_sha = _write_jsonl(oracle_path, oracle)

    old_by_key = {(int(row["source"]["seed"]), int(row["candidate_seat"])): row for row in baseline}
    transitions = Counter()
    margin_changes = []
    for row in oracle:
        key = (int(row["source"]["seed"]), int(row["candidate_seat"]))
        old = old_by_key[key]
        transitions[f"{old['outcome']}->{row['outcome']}"] += 1
        margin_changes.append(float(row["margin"]) - float(old["margin"]))
    old_patterns = _paired_patterns(baseline)
    new_patterns = _paired_patterns(oracle)
    pattern_transitions = Counter(f"{old_patterns[seed]}->{new_patterns[seed]}" for seed in sorted(new_patterns))
    old_counts = Counter(str(row["outcome"]) for row in baseline)
    new_counts = Counter(str(row["outcome"]) for row in oracle)
    branch_key = lambda row: f"{row.get('candidate_branch') or 'unknown'}/{row.get('opponent_branch') or 'unknown'}"
    summary = {
        "schema": "kaggriculture-v14-a2-parent-causal-oracle-summary-1",
        "epistemic_status": "causal oracle diagnosis on already-exposed V13 screen36; not validation and not deployable",
        "panel": str(args.panel.resolve()),
        "sources": len(records),
        "games": len(oracle),
        "candidate_parent": A2,
        "opponent": A2,
        "baseline": {
            "outcomes": dict(old_counts),
            "pure_win_rate": old_counts["W"] / len(baseline),
            "score_rate": (old_counts["W"] + 0.5 * old_counts["T"]) / len(baseline),
        },
        "oracle": {
            "outcomes": dict(new_counts),
            "pure_win_rate": new_counts["W"] / len(oracle),
            "score_rate": (new_counts["W"] + 0.5 * new_counts["T"]) / len(oracle),
            "games_with_trigger": sum(int(row["triggered_steps"]) > 0 for row in oracle),
            "sources_with_trigger": len({int(row["source"]["seed"]) for row in oracle if int(row["triggered_steps"]) > 0}),
            "eligible_steps": sum(int(row["eligible_steps"]) for row in oracle),
            "triggered_steps": sum(int(row["triggered_steps"]) for row in oracle),
            "relative_cash_gain": sum(float(row["oracle_relative_cash_gain"]) for row in oracle),
            "own_cash_gain": sum(float(row["oracle_own_cash_gain"]) for row in oracle),
        },
        "baseline_to_oracle_transitions": dict(sorted(transitions.items())),
        "paired_source_pattern_transitions": dict(sorted(pattern_transitions.items())),
        "mean_final_margin_change": sum(margin_changes) / len(margin_changes),
        "by_date": _group_outcomes(oracle, lambda row: row["source"]["date"]),
        "by_seat": _group_outcomes(oracle, lambda row: row["candidate_seat"]),
        "by_branch_pair": _group_outcomes(oracle, branch_key),
        "baseline_games": str(baseline_path.resolve()),
        "baseline_games_sha256": baseline_sha,
        "oracle_games": str(oracle_path.resolve()),
        "oracle_games_sha256": oracle_sha,
    }
    summary_path = args.output_dir / "a2_parent_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
