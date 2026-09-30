#!/usr/bin/env python3
"""Generate the execution certificate for the frozen best genome."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import optimizer


HERE = Path(__file__).resolve().parent


def main() -> int:
    genome = json.loads((HERE / "best_genome.json").read_text())
    rows = [optimizer.play(genome, seed, seat, trace=True)
            for seed in range(5000, 5012) for seat in (0, 1)]
    certs = [r["certificate"] for r in rows]
    result = {
        "engine": getattr(optimizer.KAGSIM, "ENGINE_VERSION", "1.32.7"),
        "seeds": [5000, 5011], "both_seats": True, "games": len(rows),
        "genome_valid": all(c["genome_valid"] for c in certs),
        "finance_complete": min(c["minimum_observed_cash"] for c in certs) >= 0,
        "minimum_observed_cash": min(c["minimum_observed_cash"] for c in certs),
        "maximum_units": max(c["maximum_units"] for c in certs),
        "maximum_unlocked_quadrants": max(c["maximum_unlocked_quadrants"] for c in certs),
        "minimum_daily_target_realization": min(c["minimum_daily_target_realization"] for c in certs),
        "mean_daily_target_realization": statistics.mean(c["mean_daily_target_realization"] for c in certs),
        "minimum_final_target_realization": min(c["final_daily_target_realization"] for c in certs),
        "resource_execution_complete": min(c["final_daily_target_realization"] for c in certs) >= 0.95,
        "minimum_final_bank": min(r["own"] for r in rows),
        "withheld_unaffordable_or_unneeded_orders": sum(c["runtime_ledger"]["orders_withheld"] for c in certs),
    }
    (HERE / "resource_certificate.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
