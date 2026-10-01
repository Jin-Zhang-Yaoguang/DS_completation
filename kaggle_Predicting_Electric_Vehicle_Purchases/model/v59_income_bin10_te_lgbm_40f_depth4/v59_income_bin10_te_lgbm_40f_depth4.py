# -*- coding: utf-8 -*-
"""v59：40 折 depth-4 income-bin10 LGBM，以 97.5% 训练覆盖率降低偏差。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
FULL_SEED = 49_979_687


def main() -> None:
    spec = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT_DIR = OUT_DIR
    module.base.SEED = FULL_SEED
    module.base.N_FOLDS = 40
    module.base.LGB_PARAMS["max_depth"] = 4
    module.base.LGB_PARAMS["num_leaves"] = 15
    for key in (
        "random_state",
        "bagging_seed",
        "feature_fraction_seed",
        "data_random_seed",
    ):
        module.base.LGB_PARAMS[key] = FULL_SEED
    module.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "40-fold income-bin10 TE depth-4 LightGBM, 97.5% train coverage"
    result["full_seed"] = FULL_SEED
    result["hypothesis"] = (
        "the observed 5-to-10-to-20-fold learning curve shows that larger outer-fold "
        "training coverage lowers bias; 40 folds raises coverage from 95 to 97.5 percent"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
