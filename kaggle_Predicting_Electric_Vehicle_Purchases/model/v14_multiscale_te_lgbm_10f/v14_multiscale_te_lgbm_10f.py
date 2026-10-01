# -*- coding: utf-8 -*-
"""v14：复用 v6 多尺度 TE 配方，将外层验证与测试训练比例从 80% 提高到 90%。"""

from __future__ import annotations

import importlib.util
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"


def main() -> None:
    spec = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v6：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.N_FOLDS = 10
    module.OUT_DIR = OUT_DIR
    module.main()


if __name__ == "__main__":
    main()
