from __future__ import annotations

import json
from pathlib import Path

from kaggle_Kaggriculture.model.v13_candidate_engineering import build_candidate


HERE = Path(__file__).resolve().parent


if __name__ == "__main__":
    print(
        json.dumps(
            build_candidate(
                HERE,
                model_id="v13c_a2_v8_no_wool_throttle",
                change_scope="A2仅在baseline_v8分支删除WOOL节流，baseline_v5完全不变",
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
