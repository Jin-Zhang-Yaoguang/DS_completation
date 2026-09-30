"""V14 S0/S1 静态不变量与官方引擎单步闭环检查。"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[4]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as kg

from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2
from kaggle_Kaggriculture.model.v14_first_principles_search.alternatives.s0_eod_fertilizer.main import (
    apply_eod_fertilizer_collect,
)
from kaggle_Kaggriculture.model.v14_first_principles_search.alternatives.s1_wheat_squeeze.main import (
    market_price_wheat,
    simulate_squeeze,
)


HERE = Path(__file__).resolve().parent
SCREEN_PANEL = (
    HERE.parents[1] / "v13_dual_anchor_search" / "protocol" / "screen_panel.json"
)
OUTPUT = HERE / "static_invariants.json"


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _plain(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_plain(child) for child in value]
    return value


def check_price_parity() -> dict[str, Any]:
    inventories = range(8000, 12001)
    mismatches = [
        inventory
        for inventory in inventories
        if market_price_wheat(inventory) != kg.market_price("WHEAT", inventory)
    ]
    assert not mismatches, mismatches[:10]
    return {"inventories_checked": 4001, "mismatches": 0}


def check_squeeze_math() -> dict[str, Any]:
    checked = 0
    minimum_own_gain = 10**9
    minimum_opponent_penalty = 10**9
    for inventory in range(8500, 11501, 37):
        for q in (1, 2, 3, 4, 6, 8, 12, 16, 24):
            for r in range(1, q + 1):
                for drain in (0, 1, 2, 4, 8):
                    result = simulate_squeeze(inventory, q, r, drain)
                    assert (
                        result["baseline_final_inventory"]
                        == result["candidate_final_inventory"]
                    )
                    assert result["baseline_net_wheat"] == result["candidate_net_wheat"]
                    assert result["own_gain"] >= 0, result
                    assert result["opponent_penalty"] >= 0, result
                    minimum_own_gain = min(minimum_own_gain, result["own_gain"])
                    minimum_opponent_penalty = min(
                        minimum_opponent_penalty, result["opponent_penalty"]
                    )
                    checked += 1
    return {
        "configurations_checked": checked,
        "final_market_inventory_equal": True,
        "net_wheat_equal": True,
        "minimum_own_gain": minimum_own_gain,
        "minimum_opponent_penalty": minimum_opponent_penalty,
    }


def check_s0_official_one_step() -> dict[str, Any]:
    panel = json.loads(SCREEN_PANEL.read_text(encoding="utf-8"))
    assert panel["kind"] == "screen" and panel["test_source_count"] == 0
    for source in panel["records"][:6]:
        seed = int(source["seed"])
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.reset(2)
        agents = [a2.make_agent(), a2.make_agent()]
        for step in range(0, 240):
            for state in env.state:
                state.observation.step = step
            actions = [
                agents[seat](env.state[seat].observation, env.configuration)
                for seat in (0, 1)
            ]
            controlled_flag = False
            if int(env.state[0].observation.hour) == 23:
                farm = env.state[0].observation.farms[0]
                positions = [farm.farmer, *list(farm.hands)]
                orders = [actions[0].get("farmer", ["PASS"]), *actions[0].get("hands", [])]
                for position, order in zip(positions, orders):
                    x, y = int(position[0]), int(position[1])
                    tile = farm.tiles[y][x]
                    if (
                        order
                        and str(order[0]) in {"PASS", "NORTH", "SOUTH", "EAST", "WEST"}
                        and isinstance(tile, dict)
                        and tile.get("animal")
                    ):
                        # 这是机制不变量测试，而非覆盖率估计。若真实父轨迹已在
                        # 日内收过肥料，则只把该公开 flag 控制为 True，以便让
                        # 官方引擎验证 EOD 重置边界；真实触发率留给闭环 smoke。
                        tile["fertilizer_available"] = True
                        controlled_flag = True
                        break
            modified, diag = apply_eod_fertilizer_collect(
                env.state[0].observation,
                actions[0],
                maximum_private_total=90,
            )
            if int(diag["collected_units"]) > 0:
                baseline_env = copy.deepcopy(env)
                modified_env = copy.deepcopy(env)
                baseline_env.step(actions)
                modified_env.step([modified, actions[1]])
                baseline_obs = baseline_env.state[0].observation
                modified_obs = modified_env.state[0].observation
                for field in ("farms", "market", "town", "day", "hour"):
                    assert _plain(baseline_obs[field]) == _plain(modified_obs[field]), field
                baseline_private = _plain(baseline_obs.private)
                modified_private = _plain(modified_obs.private)
                expected = copy.deepcopy(baseline_private)
                expected["shed"]["FERTILIZER"] += int(diag["collected_units"])
                assert modified_private == expected
                assert modified["market"] == actions[0].get("market", [])
                return {
                    "seed": seed,
                    "source_episode_id": str(source["episode_id"]),
                    "step": step,
                    "hour": int(env.state[0].observation.hour),
                    "collected_units": int(diag["collected_units"]),
                    "public_state_equal_after_eod": True,
                    "only_private_delta": {
                        "FERTILIZER": int(diag["collected_units"])
                    },
                    "market_orders_unchanged": True,
                    "controlled_fertilizer_flag": controlled_flag,
                }
            env.step(actions)
            if all(str(state.status) == "DONE" for state in env.state):
                break
    raise AssertionError("no resettable hour23 animal position in exposed screen prefix")


def main() -> None:
    report = {
        "schema": "kaggriculture-v14-alternative-static-invariants-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "static math plus one-step official closed loop on exposed screen source",
        "new_panel_or_test_used": False,
        "price_parity": check_price_parity(),
        "s1_inventory_neutrality": check_squeeze_math(),
        "s0_eod_public_equivalence": check_s0_official_one_step(),
        "passed": True,
    }
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
