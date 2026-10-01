# -*- coding: utf-8 -*-
"""v60：第二个独立 40 折 depth-4 LGBM，用于检验高覆盖率种子平均。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
FULL_SEED = 86_028_121


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
    result["model"] = "second 40-fold income-bin10 TE depth-4 LightGBM"
    result["full_seed"] = FULL_SEED
    result["hypothesis"] = (
        "averaging two independently folded 40-fold models should reduce split, "
        "target-encoding, and LightGBM seed variance while retaining 97.5% coverage"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
