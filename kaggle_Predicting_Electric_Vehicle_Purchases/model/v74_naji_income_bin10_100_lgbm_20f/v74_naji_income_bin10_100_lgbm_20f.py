# -*- coding: utf-8 -*-
"""v74：v69 加入 income//10 与 income//100 双尺度目标编码。"""

from __future__ import annotations

import importlib.util
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = OUT_DIR.parent / "v69_naji_lgbm_20f" / "v69_naji_lgbm_20f.py"


def main() -> None:
    spec = importlib.util.spec_from_file_location("v69_naji_lgbm_20f", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v69：{BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT_DIR = OUT_DIR
    module.EXTRA_INCOME_BINS = (10, 100)
    module.main()


if __name__ == "__main__":
    main()
