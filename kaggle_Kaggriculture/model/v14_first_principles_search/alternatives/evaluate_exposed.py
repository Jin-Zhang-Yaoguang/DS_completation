"""只在已经暴露的 V13 screen36 上评测一个 V14 alternative。

该脚本不读取 confirm/test，不调用 V13 的消费锁，也不修改正式协议。
"""

from __future__ import annotations

from dataclasses import asdict
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parents[1]
PROJECT_ROOT = MODEL_ROOT.parents[1]
V10 = MODEL_ROOT / "v10_replay_lolo_router"
for value in (str(PROJECT_ROOT), str(V10)):
    if value not in sys.path:
        sys.path.insert(0, value)

from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10  # noqa: E402
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (  # noqa: E402
    load_registry,
    registry_fingerprint,
)


SCREEN_PANEL = MODEL_ROOT / "v13_dual_anchor_search" / "protocol" / "screen_panel.json"
DEFAULT_REGISTRY = HERE / "dev_registry.json"
ANCHORS = ("v12a2_no_shop_gate", "v12_incumbent_r002")
ALLOWED_CANDIDATES = frozenset(
    {
        "v14_s0_eod_fertilizer",
        "v14_s1_inventory_neutral_wheat_squeeze",
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_records(source_count: int) -> tuple[dict[str, Any], list[v10.SeedRecord]]:
    payload = json.loads(SCREEN_PANEL.read_text(encoding="utf-8"))
    if (
        payload.get("kind") != "screen"
        or payload.get("count") != 36
        or payload.get("test_source_count") != 0
        or payload.get("historical_outcomes_accessed") is not False
    ):
        raise ValueError("screen panel exposure contract changed")
    count = 36 if int(source_count) <= 0 else int(source_count)
    if count < 1 or count > 36:
        raise ValueError("source_count must be 1..36")
    records = [
        v10.SeedRecord(
            date=str(row["date"]),
            seed=int(row["seed"]),
            episode_id=str(row["episode_id"]),
            split=str(row["split"]),
            source_path=str(row.get("source_path") or ""),
            lineage_fold=str(row.get("lineage_fold") or ""),
        )
        for row in payload["records"][:count]
    ]
    return payload, records


def _fingerprint(
    candidate: str,
    registry_hash: str,
    records: Sequence[v10.SeedRecord],
) -> str:
    payload = {
        "schema": "kaggriculture-v14-alternatives-exposed-screen-run-1",
        "candidate": candidate,
        "anchors": list(ANCHORS),
        "panel_file_sha256": _sha256(SCREEN_PANEL),
        "records": [asdict(row) for row in records],
        "registry_and_code_sha256": registry_hash,
        "evaluator_sha256": v10.implementation_fingerprint(),
        "new_panel_or_test_used": False,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _build_tasks(
    candidate: str,
    records: Sequence[v10.SeedRecord],
    fingerprint: str,
    registry_path: Path,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for anchor in ANCHORS:
        pair_id = f"{candidate}__vs__{anchor}"
        for source in records:
            for seat in (0, 1):
                text = (
                    f"{fingerprint}:{pair_id}:{source.date}:{source.episode_id}:"
                    f"{source.seed}:candidate-seat-{seat}"
                )
                tasks.append(
                    {
                        "task_id": hashlib.sha256(text.encode("utf-8")).hexdigest()[:24],
                        "run_fingerprint": fingerprint,
                        "pair_id": pair_id,
                        "model_a": candidate,
                        "model_b": anchor,
                        "model_a_seat": seat,
                        "source": asdict(source),
                        "registry": str(registry_path),
                    }
                )
    return tasks


def _find_candidate_diag(value: Any, candidate: str) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        if value.get("model_id") == candidate or value.get("kind") == candidate:
            return value
        for child in value.values():
            found = _find_candidate_diag(child, candidate)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_candidate_diag(child, candidate)
            if found is not None:
                return found
    return None


def _aggregate_diagnostics(rows: Sequence[Mapping[str, Any]], candidate: str) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    skip_reasons: Counter[str] = Counter()
    triggered_games = 0
    valid_games = 0
    trigger_key = (
        "s0_collected_units"
        if candidate == "v14_s0_eod_fertilizer"
        else "s1_executed"
    )
    scalar_keys = (
        "s0_changed_steps",
        "s0_collected_units",
        "s0_eligible_actors",
        "s0_residual_fallbacks",
        "s1_prepared",
        "s1_executed",
        "s1_unwinds",
        "s1_pending_faults",
        "s1_predicted_own_gain",
        "s1_predicted_opponent_penalty",
        "s1_predicted_relative_gain",
    )
    for row in rows:
        if row.get("error") is not None or row.get("done") is not True:
            continue
        valid_games += 1
        diagnostics = (row.get("agent_diagnostics") or {}).get(candidate, {})
        diag = _find_candidate_diag(diagnostics, candidate)
        if diag is None:
            continue
        for key in scalar_keys:
            if isinstance(diag.get(key), (int, float)):
                totals[key] += diag[key]
        for key, value in dict(
            diag.get("s0_skip_reasons") or diag.get("s1_skip_reasons") or {}
        ).items():
            skip_reasons[str(key)] += int(value or 0)
        if float(diag.get(trigger_key, 0) or 0) > 0:
            triggered_games += 1
    return {
        "valid_games": valid_games,
        "trigger_key": trigger_key,
        "triggered_games": triggered_games,
        "triggered_game_rate": triggered_games / valid_games if valid_games else None,
        "totals": dict(totals),
        "skip_reasons": dict(skip_reasons),
    }


def _summaries(
    rows: Sequence[dict[str, Any]],
    candidate: str,
    records: Sequence[v10.SeedRecord],
    tasks: Sequence[Mapping[str, Any]],
    fingerprint: str,
) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    overall = Counter()
    for anchor in ANCHORS:
        pair_id = f"{candidate}__vs__{anchor}"
        pair_ids = {
            str(task["task_id"]) for task in tasks if task["pair_id"] == pair_id
        }
        report = v10.summarise(
            list(rows),
            [candidate, anchor],
            len(records) * 2,
            pair_ids,
            fingerprint,
        )["pairs"][pair_id]
        valid = int(report["valid_games"])
        wins = int(report["wins_a"])
        ties = int(report["ties"])
        losses = int(report["losses_a"])
        report["pure_win_rate_a"] = wins / valid if valid else None
        pairs[anchor] = report
        overall.update({"valid_games": valid, "wins": wins, "ties": ties, "losses": losses})
    overall_dict = dict(overall)
    overall_dict["pure_win_rate"] = (
        overall["wins"] / overall["valid_games"] if overall["valid_games"] else None
    )
    overall_dict["score_rate"] = (
        (overall["wins"] + 0.5 * overall["ties"]) / overall["valid_games"]
        if overall["valid_games"]
        else None
    )
    return {"by_anchor": pairs, "overall": overall_dict}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=sorted(ALLOWED_CANDIDATES), required=True)
    parser.add_argument("--sources", type=int, default=0, help="0 means all exposed 36")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    registry_path = args.registry.resolve()
    registry = load_registry(registry_path)
    if registry.raw.get("test_sources_allowed") is not False:
        raise ValueError("development registry does not fail closed on test sources")
    for model_id in (args.candidate, *ANCHORS):
        registry.require(model_id)
    panel, records = _load_records(args.sources)
    fingerprint = _fingerprint(
        args.candidate, registry_fingerprint(registry), records
    )
    tasks = _build_tasks(args.candidate, records, fingerprint, registry_path)
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    output_dir.mkdir(parents=True)
    games_path = output_dir / "games.jsonl"
    rows = v10.run_tasks(tasks, games_path, int(args.workers), resume=False)
    outcomes = _summaries(rows, args.candidate, records, tasks, fingerprint)
    report = {
        "schema": "kaggriculture-v14-alternatives-exposed-screen-summary-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate": args.candidate,
        "anchors": list(ANCHORS),
        "scope": "already-exposed V13 screen36 closed loop",
        "source_count": len(records),
        "expected_games": len(tasks),
        "run_fingerprint": fingerprint,
        "panel": str(SCREEN_PANEL),
        "panel_file_sha256": _sha256(SCREEN_PANEL),
        "panel_records_sha256": panel["records_sha256"],
        "test_source_count": 0,
        "new_panel_or_test_used": False,
        "registry": str(registry_path),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "evaluation_implementation_sha256": v10.implementation_fingerprint(),
        "outcomes": outcomes,
        "diagnostics": _aggregate_diagnostics(rows, args.candidate),
        "all_done": all(row.get("done") is True and row.get("error") is None for row in rows),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
