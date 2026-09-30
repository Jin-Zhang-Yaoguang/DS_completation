"""Audit the 29-pair screen triangle and decide whether formal may open."""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from kaggle_Kaggriculture.model.v12_validation.protocol import (
    evaluator_panel,
    file_sha256,
    preflight,
    read_config,
    target_pairs,
)
from kaggle_Kaggriculture.model.v12_validation.audit_results import (
    _candidate_report,
    _source_key,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import load_registry


HERE = Path(__file__).resolve().parent


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                row = json.loads(line)
                row["_physical_line"] = line_number
                rows.append(row)
    return rows


def _pair_files(runs_dir: Path) -> dict[frozenset[str], Path]:
    result: dict[frozenset[str], Path] = {}
    for stage in ("screen_parent", "screen_pool", "screen_control"):
        directory = runs_dir / stage
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*/games.jsonl")):
            rows = _read_jsonl(path)
            identities = {
                frozenset((str(row.get("model_a")), str(row.get("model_b"))))
                for row in rows
            }
            if len(identities) != 1:
                raise ValueError(f"screen shard does not contain one pair: {path}")
            pair = next(iter(identities))
            if pair in result:
                raise ValueError(f"duplicate screen pair files: {result[pair]} and {path}")
            result[pair] = path
    return result


def audit_screen(config_path: Path, runs_dir: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    runs_dir = runs_dir.expanduser().resolve()
    preflight_report = preflight(config_path)
    config = read_config(config_path)
    registry = load_registry(config["combined_registry"])
    panel = evaluator_panel(config, "screen")
    sources = [_source_key(vars(item)) for item in panel]
    required_pairs = target_pairs(config)
    required_sets = {frozenset(pair) for pair in required_pairs}
    files = _pair_files(runs_dir)
    checks: dict[str, bool] = {
        "exact_29_pair_files": set(files) == required_sets and len(files) == 29,
        "screen_panel_18_sources": len(sources) == 18 and len(set(sources)) == 18,
    }
    errors: list[str] = []
    rows_by_pair_source: dict[
        tuple[frozenset[str], tuple[str, int, str, str]], list[dict[str, Any]]
    ] = defaultdict(list)
    result_files: list[dict[str, Any]] = []

    if checks["exact_29_pair_files"]:
        for pair_set, path in sorted(files.items(), key=lambda item: str(item[1])):
            rows = _read_jsonl(path)
            first = rows[0]
            model_ids = [str(first["model_a"]), str(first["model_b"])]
            if frozenset(model_ids) != pair_set or len(set(model_ids)) != 2:
                errors.append(f"invalid pair orientation in {path}")
                continue
            fingerprint = v10.evaluation_fingerprint(
                registry,
                model_ids,
                panel,
                int(config["screen_protocol"]["games_per_pair"]),
                False,
            )
            expected = v10.build_tasks(registry, model_ids, panel, fingerprint, False)
            expected_by_id = {str(task["task_id"]): task for task in expected}
            if len(rows) != 36 or len(expected_by_id) != 36:
                errors.append(f"screen pair is not exactly 36 rows: {path}")
                continue
            if len({str(row.get("task_id")) for row in rows}) != 36:
                errors.append(f"duplicate task_id in {path}")
                continue
            for row in rows:
                task = expected_by_id.get(str(row.get("task_id")))
                try:
                    if task is None:
                        raise ValueError("foreign task_id")
                    for key in (
                        "run_fingerprint",
                        "pair_id",
                        "model_a",
                        "model_b",
                        "model_a_seat",
                    ):
                        if row.get(key) != task[key]:
                            raise ValueError(f"{key} mismatch")
                    if row.get("schema") != v10.SCHEMA:
                        raise ValueError("schema mismatch")
                    if _source_key(row["source"]) != _source_key(task["source"]):
                        raise ValueError("source mismatch")
                    seat = int(row["model_a_seat"])
                    expected_seats = (
                        [row["model_a"], row["model_b"]]
                        if seat == 0
                        else [row["model_b"], row["model_a"]]
                    )
                    if list(row.get("seat_models") or []) != expected_seats:
                        raise ValueError("seat_models mismatch")
                    if row.get("error") is not None or row.get("done") is not True:
                        raise ValueError("error/non-DONE row")
                    if list(row.get("statuses") or []) != ["DONE", "DONE"]:
                        raise ValueError("terminal statuses mismatch")
                    rows_by_pair_source[
                        (pair_set, _source_key(row["source"]))
                    ].append(row)
                except Exception as exc:
                    errors.append(
                        f"{path}:{row.get('_physical_line')}:{type(exc).__name__}:{exc}"
                    )
            result_files.append(
                {
                    "pair": sorted(pair_set),
                    "path": str(path),
                    "file_sha256": file_sha256(path),
                    "run_fingerprint": fingerprint,
                    "rows": len(rows),
                }
            )

    checks["all_rows_exact_and_done"] = not errors
    checks["each_pair_common_panel_two_seats"] = (
        checks["exact_29_pair_files"]
        and all(
            len(rows_by_pair_source[(frozenset(pair), source)]) == 2
            and {
                int(row["model_a_seat"])
                for row in rows_by_pair_source[(frozenset(pair), source)]
            }
            == {0, 1}
            for pair in required_pairs
            for source in sources
        )
    )
    integrity = all(checks.values())
    candidate_reports: list[dict[str, Any]] = []
    if integrity:
        for item in config["candidates"]:
            report = _candidate_report(
                str(item["id"]),
                str(item["parent"]),
                [str(value) for value in config["strong_opponents"]],
                sources,
                rows_by_pair_source,
                config["quality_thresholds"],
            )
            common = report["common_opponent_uplift"]
            direct = report["direct_parent"]
            thresholds = config["screen_thresholds"]
            gates = {
                "direct_parent_score_point": direct["score_rate"]
                >= float(thresholds["direct_parent_score_point_min"]),
                "common_opponent_uplift_point": common["score_uplift"]
                >= float(thresholds["common_opponent_uplift_point_min"]),
                "worst_common_opponent_point": common[
                    "worst_opponent_score_uplift"
                ]
                >= float(thresholds["worst_common_opponent_point_min"]),
            }
            report["screen_formal_gates"] = gates
            report["screen_formal_ready"] = all(gates.values())
            candidate_reports.append(report)

    return {
        "schema": "kaggriculture-v12-screen-triangle-audit-1",
        "read_only": True,
        "config": str(config_path),
        "config_file_sha256": file_sha256(config_path),
        "preflight": preflight_report,
        "expected_pairs": 29,
        "expected_games": 29 * 36,
        "checks": checks,
        "integrity_passed": integrity,
        "errors": errors[:50],
        "result_files": result_files,
        "candidate_parent_uplift": candidate_reports,
        "all_candidates_formal_ready": bool(candidate_reports)
        and all(report["screen_formal_ready"] for report in candidate_reports),
        "note": "screen uses only the independent 18-source panel; formal panel remains unopened",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=HERE / "frozen_v4" / "validation_config.json"
    )
    parser.add_argument("--runs", type=Path, default=HERE / "runs_v4")
    parser.add_argument(
        "--output", type=Path, default=HERE / "runs_v4" / "screen_audit.json"
    )
    args = parser.parse_args()
    report = audit_screen(args.config, args.runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "integrity_passed": report["integrity_passed"],
                "all_candidates_formal_ready": report[
                    "all_candidates_formal_ready"
                ],
            },
            ensure_ascii=False,
        )
    )
    if not report["integrity_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
