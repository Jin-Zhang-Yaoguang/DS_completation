#!/usr/bin/env python3
"""汇总 R2.1-A 逐局损失账本；本地面板只能生成工程诊断，不能生成强度结论。"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
CATEGORY_MODULE = {
    "FINANCING_SHORTFALL": "I4 市场与融资",
    "MISSED_HIGH_PRICE_SALE": "I4 市场与融资",
    "FEED_SHORTAGE": "I4 市场与融资",
    "OVERDUE_TASK": "I3 统一执行器",
    "UNPRODUCTIVE_MOVE": "I3 统一执行器",
    "INVENTORY_OVERHANG": "I4 市场与融资",
    "TERMINAL_UNREALIZED": "I4 市场与终局",
}


def summarize(payload: dict[str, Any], source: Path) -> dict[str, Any]:
    rows = list(payload.get("rows") or [])
    if not rows:
        raise ValueError("input has no per-game rows")
    values: dict[str, list[float]] = {}
    events: Counter[str] = Counter()
    units: Counter[str] = Counter()
    per_game_top: list[dict[str, Any]] = []
    for row in rows:
        attribution = dict(row.get("loss_attribution") or {})
        if attribution.get("schema") != "v117-r2.1-a-loss-attribution-v1":
            raise ValueError("row missing R2.1-A loss schema")
        totals = dict(attribution.get("totals") or {})
        for category, metric in totals.items():
            metric = dict(metric)
            values.setdefault(str(category), []).append(float(metric.get("estimated_value", 0.0)))
            events[str(category)] += int(metric.get("events", 0))
            units[str(category)] += float(metric.get("units", 0.0))
        per_game_top.append({
            "seed": row.get("seed"), "seat": row.get("seat"),
            "top_losses": list(attribution.get("top_losses") or []),
        })
    category_rows = []
    for category, series in values.items():
        category_rows.append({
            "category": category,
            "mean_proxy_value_per_game": statistics.mean(series),
            "median_proxy_value_per_game": statistics.median(series),
            "maximum_proxy_value": max(series),
            "presence_rate": statistics.mean(value > 0 for value in series),
            "events": int(events[category]),
            "units": float(units[category]),
            "candidate_module": CATEGORY_MODULE.get(category, "待人工归因"),
        })
    category_rows.sort(key=lambda row: (-float(row["mean_proxy_value_per_game"]), str(row["category"])))
    dominant = category_rows[0] if category_rows else None
    return {
        "schema": "v117-r2.1-a-loss-attribution-summary-v1",
        "source_file": str(source),
        "panel_type": "LOCAL_ENGINEERING_ONLY",
        "games": len(rows),
        "evidence_boundary": (
            "Local arbitrary seeds validate instrumentation and rank diagnostic proxies only; "
            "they do not validate V1 win rate, expert qualification, Router strength, or R2.1 exit gates."
        ),
        "category_ranking": category_rows,
        "per_game_top_three": per_game_top,
        "dominant_proxy": dominant,
        "next_candidate_module": dominant.get("candidate_module") if dominant else "保持冻结",
        "decision_status": "ENGINEERING_DIAGNOSTIC_ONLY_REPLAY_PANEL_REQUIRED",
        "replay_strength_claim_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "loss_attribution_r2_1_a_report.json")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = summarize(payload, args.input)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "per_game_top_three"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
