from __future__ import annotations

import json
from pathlib import Path

from kaggle_Kaggriculture.model.v13_candidate_engineering import package_qa
from kaggle_Kaggriculture.model.v13d_a2_public_winrisk_gate import main


HERE = Path(__file__).resolve().parent


if __name__ == "__main__":
    report = package_qa(
        HERE,
        main,
        model_id="v13d_a2_public_winrisk_gate",
        effect_counter_key="lead_bypass_steps",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["verdict"] != "PASS":
        raise SystemExit(1)
