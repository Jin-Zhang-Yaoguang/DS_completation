# -*- coding: utf-8 -*-
"""v37：把独立外层切分的 v36 加入 v34 的收入-bin10 bag。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v34_blend_bin10_bag_v28" / "v34_blend_bin10_bag_v28.py"


def main() -> None:
    spec = importlib.util.spec_from_file_location("v34_blend_bin10_bag_v28", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v34：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT_DIR = OUT_DIR
    module.BIN10_MEMBERS = (
        "v31_income_bin10_te_lgbm_10f_seed2026",
        "v32_income_bin10_te_lgbm_10f_seed3407",
        "v36_income_bin10_te_lgbm_10f_fullseed2718",
    )
    module.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = (
        "v16 public/MLP weights with three-member cross-fold bin10 bag, then v28 blend"
    )
    result["hypothesis"] = (
        "average model-seed and outer-fold-seed variance before adding the complementary "
        "20-fold prediction path"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
