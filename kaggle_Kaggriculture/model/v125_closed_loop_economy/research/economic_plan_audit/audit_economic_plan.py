"""三类人工可见状态的高层计划审计，不生成新策略或完整对局。"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "r6_frozen_source.py"
RULES = importlib.import_module("kaggle_environments.envs.kaggriculture.kaggriculture")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load():
    assert sha(SOURCE) == "b599d1653380aa2d9033a5aaf190e6f01f601d69cfa092d4ab40e37f8393a58c"
    assert sha(RULES.__file__) == "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
    spec = importlib.util.spec_from_file_location("r6_economic_audit", SOURCE)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def observation(day=12, hour=8, regime="dairy"):
    farm = {"farmer": [4, 4], "hands": [], "hires_today": 0, "money": 40000,
            "unlocked_quadrants": ["NW", "NE", "SW", "SE"], "tiles": [[None] * 10 for _ in range(10)]}
    obs = {"player": 0, "step": 24 * day + hour, "day": day, "hour": hour,
           "farms": [farm, deepcopy(farm)], "private": {"shed": {}, "inventories": [{}], "seeds": {}},
           "town": {"unlocked_shops": []}, "market": RULES._new_market()}
    quote_regime(obs, regime)
    return obs


def quote_regime(obs, regime):
    # 报价总由真实市场库存函数导出；只切换两种预先指定的压力状态。
    obs["market"]["inventory"]["MILK"] = 8000 if regime == "dairy" else 12000
    obs["market"]["inventory"]["WOOL"] = 10000 if regime == "dairy" else 8000
    RULES._refresh_prices(obs["market"])


def plan_call(mod, obs):
    st = mod.new_state(obs)
    plan = mod.economic_plan(obs, st)
    tasks = mod.make_tasks(obs, st, plan)
    actions = [["PASS"] for _ in obs["private"]["inventories"]]
    orders = mod.market_orders(obs, st, plan, tasks, actions)
    return {"observation": deepcopy(obs), "expert": st["expert"], "forecasts": st["forecasts"],
            "crop_scores": st["crop_scores"], "plan": plan, "orders": orders,
            "feed_task_count": sum(any(op[0] == "FEED" for op in task["ops"]) for task in tasks)}


def place_animals(obs, animals, placed_day):
    index = 0
    for animal, number in animals.items():
        for _ in range(number):
            x, y = index % 10, index // 10
            obs["farms"][0]["tiles"][y][x] = RULES._new_animal(animal, placed_day)
            index += 1


def daily_production_probe(farm, current_day, horizon):
    """仅调用官方纯日终动物刷新；人工保证每日喂/护理和及时清空产物。"""
    farm = deepcopy(farm)
    rows = []
    for day in range(current_day, current_day + horizon):
        animals = [t for row in farm["tiles"] for t in row if isinstance(t, dict) and t.get("animal")]
        for tile in animals:
            tile["fed_today"] = True
            tile["cared_today"] = True
            tile["yield_units"] = 0
        RULES._daily_refresh_animals(farm, day)
        rows.append({"next_day": day + 1, "output_units": sum(t["yield_units"] for t in animals),
                     "fed_and_cared_animal_count": len(animals)})
    return rows


def main():
    mod = load(); checks = {}; scenarios = {}

    # 一：只改变摆放日；高层预测不变，当前六天真实产出窗口却不同。
    mature = observation(day=8)
    place_animals(mature, {"COW": 4}, placed_day=0)
    immature = deepcopy(mature)
    for row in immature["farms"][0]["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                tile["placed_day"] = 8
    old, young = plan_call(mod, mature), plan_call(mod, immature)
    old_output = daily_production_probe(mature["farms"][0], 8, 6)
    young_output = daily_production_probe(immature["farms"][0], 8, 6)
    checks["age_only_change_identical_forecasts"] = old["forecasts"] == young["forecasts"] and old["expert"] == young["expert"] and old["plan"] == young["plan"]
    checks["same_animal_count_different_six_day_product_window"] = sum(x["output_units"] for x in old_output) > 0 and sum(x["output_units"] for x in young_output) == 0
    scenarios["maturity_blind_forecast"] = {"mature": old, "newly_placed": young, "official_daily_mature": old_output,
                                               "official_daily_new": young_output, "r6_six_day_predicted_milk_gross_units": 4 * 1.5 * 6,
                                               "boundary": "纯规则日终控制强制每日喂养和护理并及时清空产物，不包含领取、移动、销售、劳力可行性或真实价格路径；不是完整收益。"}

    # 二：逐项改变饲料报价、现金、可用劳力，分清计划遗漏与市场现金保护。
    cheap = observation(); expensive = deepcopy(cheap)
    expensive["market"]["inventory"]["WHEAT"] = -10000000
    RULES._refresh_prices(expensive["market"])
    cheap_plan, expensive_plan = plan_call(mod, cheap), plan_call(mod, expensive)
    cashless = deepcopy(cheap); cashless["farms"][0]["money"] = 0
    cashless_plan = plan_call(mod, cashless)
    checks["wheat_cost_ignored_by_expert_and_animal_cap"] = cheap_plan["expert"] == expensive_plan["expert"] == "dairy" and cheap_plan["plan"]["animals"] == expensive_plan["plan"]["animals"] and cheap_plan["forecasts"]["MILK"] == expensive_plan["forecasts"]["MILK"]
    checks["zero_cash_plan_unchanged_but_market_blocks_purchase"] = cashless_plan["plan"]["animals"] == cheap_plan["plan"]["animals"] and not any(order[0] == "BUY_ANIMAL" for order in cashless_plan["orders"])
    crowded = observation(regime="fiber")
    place_animals(crowded, {"COW": 14, "SHEEP": 3}, placed_day=4)
    staffed = deepcopy(crowded)
    staffed["farms"][0]["hands"] = [[4, 4] for _ in range(12)]
    staffed["farms"][0]["hires_today"] = 12
    staffed["private"]["inventories"] = [{} for _ in range(13)]
    crowded_plan, staffed_plan = plan_call(mod, crowded), plan_call(mod, staffed)
    remaining_slots = 24 - crowded["hour"]
    checks["labor_does_not_change_high_level_plan"] = crowded_plan["plan"] == staffed_plan["plan"] and crowded_plan["forecasts"] == staffed_plan["forecasts"]
    checks["existing_daily_feed_demands_exceed_one_worker_slots"] = crowded_plan["feed_task_count"] == 17 > remaining_slots and not any(order[0] == "HIRE" for order in crowded_plan["orders"])
    checks["extra_sheep_requested_while_existing_daily_feed_plan_over_capacity"] = ["BUY_ANIMAL", "SHEEP", 1] in crowded_plan["orders"] and crowded_plan["plan"]["animals"] == {"GOOSE": 0, "COW": 14, "SHEEP": 13}
    scenarios["missing_resource_budget"] = {"cheap_feed": cheap_plan, "expensive_feed": expensive_plan, "zero_cash_control": cashless_plan,
                                                "one_worker": crowded_plan, "thirteen_workers_control": staffed_plan,
                                                "remaining_unit_action_slots_one_worker": remaining_slots,
                                                "feed_price_only_stress": "极端但由当前规则价格函数产生的人工可见库存；未声称自然频率。",
                                                "labor_boundary": "17项FEED大于16剩余动作即使零移动也不可全做。未喂当天不必立即逃逸，购买对未来也未必无价值；反例针对缺少共享预算和可行性声明。"}

    # 三：可控报价切换，真实固定价提交动物采购，其他订单只记录不执行。
    switching = observation(day=12, hour=8)
    timeline = []
    for phase, regime in enumerate(("dairy", "fiber", "dairy")):
        quote_regime(switching, regime)
        for call in range(40):
            result = plan_call(mod, switching)
            requests = [order for order in result["orders"] if order[0] == "BUY_ANIMAL"]
            before = deepcopy(switching["private"]["shed"])
            fills = []
            for order in requests:
                for _ in range(order[2]):
                    accepted = RULES._commit_unit("BUY_ANIMAL", order[1], RULES.ANIMALS[order[1]]["cost"],
                                                   switching["farms"][0], switching["private"], switching["market"], 100)
                    fills.append({"order": order, "accepted": accepted})
            timeline.append({"phase": phase, "regime": regime, "call_in_phase": call, "day": switching["day"], "hour": switching["hour"],
                             "expert": result["expert"], "plan_animals": result["plan"]["animals"], "forecast": result["forecasts"],
                             "before_shed": before, "orders": result["orders"], "animal_fills": fills,
                             "after_shed": deepcopy(switching["private"]["shed"]), "after_cash": switching["farms"][0]["money"]})
            purchase_window = switching["hour"] <= 18
            switching["step"] += 1
            switching["day"], switching["hour"] = divmod(switching["step"], 24)
            if not requests and purchase_window:
                break
        else:
            raise AssertionError("预定40个局部调用内未达到该阶段目标")
    ends = [next(row for row in reversed(timeline) if row["phase"] == phase) for phase in range(3)]
    checks["first_dairy_purchases_reach14cow3sheep"] = ends[0]["after_shed"] == {"COW": 14, "SHEEP": 3}
    checks["fiber_switch_retains_cows_and_adds_ten_sheep"] = ends[1]["after_shed"] == {"COW": 14, "SHEEP": 13}
    checks["switch_back_does_not_remove_surplus_or_buy_more"] = ends[2]["after_shed"] == ends[1]["after_shed"] and not ends[2]["animal_fills"]
    checks["all_selected_animal_purchases_official_commit_accepted"] = all(fill["accepted"] for row in timeline for fill in row["animal_fills"])
    checks["consecutive_plan_calls_advance_clock_once"] = all(24 * b["day"] + b["hour"] == 24 * a["day"] + a["hour"] + 1 for a, b in zip(timeline, timeline[1:]))
    scenarios["irreversible_target_union"] = {"initial_observation": observation(day=12, hour=8), "timeline": timeline,
                                                "phase_end_states": ends, "final_observation": switching,
                                                "scope": "调用冻结economic_plan/make_tasks/market_orders，仅用官方_commit_unit落实其BUY_ANIMAL；未执行其他市场订单、单位动作、日终或商店RNG。按真实钟表推进可采购时段；报价切换由人工指定。动物库存均为已购未放置。",
                                                "meaning": "证明保留存量与放行另一专家新增目标会叠加为14牛13羊，非任何单个专家组合；不证明27只必然亏损或建议删除已有资产。"}
    output = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "candidate_sha256": sha(SOURCE),
              "rules_sha256": sha(RULES.__file__), "harness_sha256": sha(__file__), "candidate_agent_calls": 0,
              "full_interpreter_games": 0, "new_replay_reads": 0, "workers": 1,
              "checks": checks, "pass": all(checks.values()), "scenarios": scenarios}
    (HERE / "audit_results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"pass": output["pass"], "checks": checks,
                      "mature_six_day_units": sum(x["output_units"] for x in old_output),
                      "young_six_day_units": sum(x["output_units"] for x in young_output),
                      "feed_prices": [cheap["market"]["prices"]["WHEAT"], expensive["market"]["prices"]["WHEAT"]],
                      "union_phases": [{k: row[k] for k in ("day", "hour", "expert", "after_shed", "after_cash")} for row in ends],
                      "plan_timeline_calls": len(timeline)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
