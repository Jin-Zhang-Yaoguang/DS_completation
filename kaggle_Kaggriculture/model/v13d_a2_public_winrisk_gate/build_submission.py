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
                model_id="v13d_a2_public_winrisk_gate",
                change_scope="A2仅在自己公开money严格领先时跳过top-day节流；缺字段、平局或落后均保持A2",
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
