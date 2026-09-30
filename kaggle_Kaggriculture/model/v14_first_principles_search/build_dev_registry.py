"""Build the discovery-only registry for the V14 queue solver."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
V13_REGISTRY = MODEL_ROOT / "v13_dual_anchor_search" / "protocol" / "clean_screen_registry.json"
OUTPUT = HERE / "dev_registry.json"


def main() -> None:
    source = json.loads(V13_REGISTRY.read_text(encoding="utf-8"))
    a2 = next(item for item in source["models"] if item["id"] == "v12a2_no_shop_gate")
    r002 = next(item for item in source["models"] if item["id"] == "v12_incumbent_r002")
    candidate = {
        "id": "v14_queue_best_response",
        "kind": "python",
        "path": str((HERE / "prototype_queue_solver.py").resolve()),
        "factory": "make_agent",
        "code_paths": [
            str((HERE / "prototype_queue_solver.py").resolve()),
            str((MODEL_ROOT / "v12a2_no_shop_gate" / "main.py").resolve()),
            str((MODEL_ROOT / "v12a_terminal_branch_guard" / "main.py").resolve()),
            str((MODEL_ROOT / "v10_replay_lolo_router" / "agent_factory.py").resolve()),
            str((MODEL_ROOT / "v10_replay_lolo_router" / "expert_registry.py").resolve()),
            str((MODEL_ROOT / "v10_replay_lolo_router" / "router.py").resolve()),
            str((MODEL_ROOT / "v10_replay_lolo_router" / "variants.py").resolve()),
            str((MODEL_ROOT / "v10_replay_lolo_router" / "learned_router_weights.npz").resolve()),
            str((MODEL_ROOT / "v11_iterative_league" / "fast_router.py").resolve()),
        ],
        "family": "a2+stateful_opponent_shadow_queue_best_response",
        "lineage": ["v12a2_no_shop_gate", "v14_queue_best_response"],
        "tags": [
            "development-only",
            "market-order",
            "stateful-opponent-shadow",
            "quantity-conserving",
        ],
    }
    combined = {
        **candidate,
        "id": "v14_queue_shadow_plus_wheat_squeeze",
        "path": str((HERE / "prototype_queue_s1_combined.py").resolve()),
        "code_paths": [
            str((HERE / "prototype_queue_s1_combined.py").resolve()),
            *candidate["code_paths"],
            str((HERE / "alternatives" / "s1_wheat_squeeze" / "main.py").resolve()),
            str((MODEL_ROOT / "v8_kawa_lead2_slot" / "main.py").resolve()),
        ],
        "family": "a2+stateful_queue_br+inventory_neutral_wheat_squeeze",
        "lineage": [
            "v12a2_no_shop_gate",
            "v14_s1_inventory_neutral_wheat_squeeze",
            "v14_queue_shadow_plus_wheat_squeeze",
        ],
        "tags": [*candidate["tags"], "inventory-neutral-market-interference"],
    }
    no_mirror = {
        **candidate,
        "id": "v14_queue_stateful_no_mirror",
        "path": str((HERE / "prototype_queue_solver_no_mirror.py").resolve()),
        "code_paths": [
            str((HERE / "prototype_queue_solver_no_mirror.py").resolve()),
            *candidate["code_paths"],
        ],
        "family": "a2+stateful-opponent-shadow+queue-br-no-public-equality",
        "lineage": [
            "v12a2_no_shop_gate",
            "v14_queue_best_response",
            "v14_queue_stateful_no_mirror",
        ],
        "tags": [
            *candidate["tags"],
            "full-public-conformance",
            "public-equality-removed",
            "clone-distance-retained",
        ],
    }
    payload = {
        "schema": "kaggriculture-v14-development-registry-1",
        "purpose": "exposed V13 source mechanism discovery only",
        "test_sources_allowed": False,
        "models": [candidate, no_mirror, combined, a2, r002],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
