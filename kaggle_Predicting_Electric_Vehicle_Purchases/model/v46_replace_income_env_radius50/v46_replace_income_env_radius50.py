# -*- coding: utf-8 -*-
"""v46：等维消融，将 v29 的精确 income×env TE 替换为 ±50 中心邻域 TE。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v45_income_env_radius50_te_lgbm" / "v45_income_env_radius50_te_lgbm.py"


def main() -> None:
    spec = importlib.util.spec_from_file_location("v45_radius_recipe", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v45：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.base.OUT_DIR = OUT_DIR
    module.base.factorize_joint_extended = module.factorize_joint_extended
    module.base.base.encode_key = module.encode_key_extended
    module.base.base.SMOOTHS = (5.0, 15.0, 80.0)
    module.base.base.TE_KEYS["income_bin10"] = ["_income_bin10"]
    module.base.base.TE_KEYS["income_env"] = ["_income_env_radius50"]
    module.base.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v29 with exact income-env TE replaced by centered +/-50 TE"
    result["income_environment_radius"] = module.RADIUS
    result["hypothesis"] = (
        "hold feature count and column-sampling probability fixed while testing "
        "whether the stronger univariate centered-neighborhood estimate should "
        "replace, rather than augment, exact income-environment TE"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
