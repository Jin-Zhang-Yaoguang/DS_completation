"""构建仅供已暴露 screen36 使用的 V14 alternatives 注册表。"""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parents[1]
SOURCE = MODEL_ROOT / "v13_dual_anchor_search" / "protocol" / "clean_screen_registry.json"
OUTPUT = HERE / "dev_registry.json"


def _candidate(model_id: str, relative_main: str, tags: list[str]) -> dict:
    path = (HERE / relative_main).resolve()
    dependencies = [
        path,
        MODEL_ROOT / "v12a2_no_shop_gate" / "main.py",
        MODEL_ROOT / "v12a_terminal_branch_guard" / "main.py",
        MODEL_ROOT / "v8_kawa_lead2_slot" / "main.py",
        MODEL_ROOT / "v10_replay_lolo_router" / "agent_factory.py",
        MODEL_ROOT / "v10_replay_lolo_router" / "expert_registry.py",
        MODEL_ROOT / "v10_replay_lolo_router" / "router.py",
        MODEL_ROOT / "v10_replay_lolo_router" / "variants.py",
        MODEL_ROOT / "v10_replay_lolo_router" / "learned_router_weights.npz",
        MODEL_ROOT / "v11_iterative_league" / "fast_router.py",
        MODEL_ROOT / "v11_iterative_league" / "runs" / "round_002" / "strategy" / "registry_next.json",
    ]
    return {
        "id": model_id,
        "kind": "python",
        "path": str(path),
        "factory": "make_agent",
        "code_paths": [str(value.resolve()) for value in dependencies],
        "family": f"a2+{model_id}",
        "lineage": ["v12a2_no_shop_gate", model_id],
        "tags": ["development-only", "a2-descendant", *tags],
    }


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    anchors = {
        str(row["id"]): row
        for row in source["models"]
        if row["id"] in {"v12a2_no_shop_gate", "v12_incumbent_r002"}
    }
    if set(anchors) != {"v12a2_no_shop_gate", "v12_incumbent_r002"}:
        raise ValueError("clean screen registry is missing an anchor")
    payload = {
        "schema": "kaggriculture-v14-alternatives-development-registry-1",
        "purpose": "already-exposed V13 screen36 mechanism falsification only",
        "test_sources_allowed": False,
        "models": [
            _candidate(
                "v14_s0_eod_fertilizer",
                "s0_eod_fertilizer/main.py",
                ["hour23", "fertilizer", "worker-residual"],
            ),
            _candidate(
                "v14_s1_inventory_neutral_wheat_squeeze",
                "s1_wheat_squeeze/main.py",
                ["wheat", "two-turn", "inventory-neutral", "market-interference"],
            ),
            anchors["v12a2_no_shop_gate"],
            anchors["v12_incumbent_r002"],
        ],
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
