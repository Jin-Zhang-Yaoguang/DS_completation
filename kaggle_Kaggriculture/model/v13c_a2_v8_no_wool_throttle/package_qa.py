from __future__ import annotations

import json
from pathlib import Path

from kaggle_Kaggriculture.model.v13_candidate_engineering import package_qa
from kaggle_Kaggriculture.model.v13c_a2_v8_no_wool_throttle import main


HERE = Path(__file__).resolve().parent


if __name__ == "__main__":
    report = package_qa(
        HERE,
        main,
        model_id="v13c_a2_v8_no_wool_throttle",
        effect_counter_key="v8_wool_throttle_opportunities",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["verdict"] != "PASS":
        raise SystemExit(1)
