"""Combine the two already-run exposed shadow calibration shards."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from calibrate_shadow import _read_jsonl, _summarise, _write_jsonl


HERE = Path(__file__).resolve().parent


def main() -> None:
    game_paths = [HERE / "screen36_games.jsonl", HERE / "confirm100_games.jsonl"]
    opportunity_paths = [
        HERE / "screen36_opportunities.jsonl",
        HERE / "confirm100_opportunities.jsonl",
    ]
    for path in [*game_paths, *opportunity_paths]:
        if not path.is_file():
            raise FileNotFoundError(path)
    games = [row for path in game_paths for row in _read_jsonl(path)]
    opportunities = [row for path in opportunity_paths for row in _read_jsonl(path)]
    games.sort(key=lambda row: (row["panel"], int(row["source"]["seed"]), int(row["candidate_seat"])))
    opportunities.sort(
        key=lambda row: (
            row["panel"], int(row["source"]["seed"]),
            int(row["candidate_seat"]), int(row["step"]),
        )
    )
    games_path = HERE / "combined_games.jsonl"
    opportunities_path = HERE / "combined_opportunities.jsonl"
    summary_path = HERE / "combined_summary.json"
    games_sha = _write_jsonl(games_path, games)
    opportunities_sha = _write_jsonl(opportunities_path, opportunities)
    summary = _summarise(opportunities, games)
    summary.update({
        "games_file": str(games_path.resolve()),
        "games_sha256": games_sha,
        "opportunities_file": str(opportunities_path.resolve()),
        "opportunities_sha256": opportunities_sha,
        "input_shards": {
            str(path.name): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [*game_paths, *opportunity_paths]
        },
    })
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    curve_path = HERE / "coverage_precision.csv"
    with curve_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "method", "gate", "selected", "coverage", "queue_exact",
            "queue_false_positive", "queue_precision", "queue_wilson95_lower",
            "multiset_precision", "sell_qty_precision", "exec_cap_precision",
        ])
        writer.writeheader()
        for method, values in summary["coverage_precision"].items():
            for value in values:
                writer.writerow({"method": method, **value})
    segment_path = HERE / "segment_metrics.csv"
    with segment_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "method", "dimension", "segment", "opportunities",
            "queue_exact_rate", "shed_exact_rate", "exec_cap_exact_rate",
        ])
        writer.writeheader()
        for method, payload in summary["methods"].items():
            for dimension in ("by_panel", "by_date", "by_seat", "by_branch"):
                for segment, metrics in payload[dimension].items():
                    writer.writerow({
                        "method": method,
                        "dimension": dimension,
                        "segment": segment,
                        "opportunities": metrics["opportunities"],
                        "queue_exact_rate": metrics["queue_exact"]["rate"],
                        "shed_exact_rate": metrics["shed_exact"]["rate"],
                        "exec_cap_exact_rate": metrics["actual_queue_exec_cap_exact"]["rate"],
                    })
    summary["coverage_precision_csv"] = str(curve_path.resolve())
    summary["coverage_precision_csv_sha256"] = hashlib.sha256(curve_path.read_bytes()).hexdigest()
    summary["segment_metrics_csv"] = str(segment_path.resolve())
    summary["segment_metrics_csv_sha256"] = hashlib.sha256(segment_path.read_bytes()).hexdigest()
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "summary": str(summary_path.resolve()),
        "games": len(games),
        "opportunities": len(opportunities),
        "recommended_gate": summary["recommended_preregistered_gate"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
