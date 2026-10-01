# -*- coding: utf-8 -*-
"""v28：复用 v6 配方，将外层训练覆盖率由 10 折的 90% 提高到 20 折的 95%。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"


def main() -> None:
    spec = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v6：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.N_FOLDS = 20
    module.OUT_DIR = OUT_DIR
    module.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "multiscale nested TE LightGBM with 20 outer folds"
    result["hypothesis"] = (
        "raise each model's labeled training coverage from 90 to 95 percent; "
        "the prior 5-to-10-fold change improved OOF by about 0.00015"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
