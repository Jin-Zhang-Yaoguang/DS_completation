# -*- coding: utf-8 -*-
"""v33：隔离测试高分辨率 LightGBM histogram 是否仍能补充多尺度精确值 TE。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
BASE_PATH = OUT_DIR.parent / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
SPEC = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"无法载入 {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


def main() -> None:
    base.OUT_DIR = OUT_DIR
    base.LGB_PARAMS["max_bin"] = 16384
    base.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v6 multiscale nested TE with max_bin=16384"
    result["hypothesis"] = (
        "resolve all 13214 exact income values in raw-value histograms; test whether "
        "that ordered signal remains complementary after exact-value target encoding"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
