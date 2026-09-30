"""Pure compiler/isolated legacy-function controls. No agent or engine is called."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
from datetime import datetime, timezone
import ast
import hashlib
import json
import calendar_compiler as compiler

HERE = Path(__file__).resolve().parent
MODEL = next(p for p in HERE.parents if p.name == "v125_closed_loop_economy")
PARENT = MODEL / "candidates/V125-R9/main.py"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PARENT) == compiler.PARENT_SOURCE_SHA256
tree = ast.parse(PARENT.read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "project_calendar")
namespace = {"Counter": Counter, "CROPS": compiler.CROPS, "ANIMALS": compiler.ANIMALS,
             "dist": compiler.dist, "home": compiler.home}
# Only the single original calendar function is compiled, never the candidate module.
exec(compile(ast.Module(body=[function], type_ignores=[]), "isolated_frozen_r9_calendar", "exec"), namespace)
legacy = namespace["project_calendar"]
checks, comparisons = {}, []
legacy_calls = enriched_calls = 0


def enrich(t, day=0, hour=0, pos=(3, 4)):
    global enriched_calls
    enriched_calls += 1
    return compiler.project_calendar_with_services(t, day, hour, pos)


def plant(crop, born=0, yield_units=None):
    spec = compiler.CROPS[crop]
    return {"kind": "PLANT", "crop": crop, "planted_day": born,
            "yield_units": (0 if spec[3] else 1) if yield_units is None else yield_units,
            "watered_today": False, "consecutive_unwatered": 1, "fertilized_until_day": -1,
            "max_lifespan_step": -1 if spec[3] else (born + spec[2] + 1) * 24}


def animal(kind, born=0):
    return {"kind": compiler.ANIMALS[kind][1], "animal": kind, "placed_day": born,
            "yield_units": 0, "fed_today": False, "cared_today": False,
            "consecutive_unfed": 0, "fertilizer_available": False, "pending_care_bonus": 0}


for item in list(compiler.CROPS) + list(compiler.ANIMALS):
    for day in range(30):
        for hour in (0, 7, 22):
            for cared in (False, True):
                t = plant(item) if item in compiler.CROPS else animal(item)
                if item in compiler.CROPS:
                    t["watered_today"] = cared
                    t["fertilized_until_day"] = day + 1 if cared else -1
                else:
                    t["fed_today"] = cared
                    t["cared_today"] = cared
                    t["yield_units"] = 2 if cared else 0
                    t["fertilizer_available"] = cared
                    t["pending_care_bonus"] = 3 if cared else 0
                before = deepcopy(t)
                old = legacy(t, day, hour, (3, 4)); legacy_calls += 1
                new = enrich(t, day, hour)
                equal = all(old[k] == new[k] for k in ("goods", "work", "feed"))
                comparisons.append({"item": item, "day": day, "hour": hour, "care_variant": cared,
                                    "legacy_equal": equal, "input_unchanged": t == before})
checks["all_1440_legacy_value_comparisons_equal"] = len(comparisons) == 1440 and all(r["legacy_equal"] for r in comparisons)
checks["all_inputs_unchanged"] = all(r["input_unchanged"] for r in comparisons)

cow = enrich(animal("COW"))
checks["cow_first_production_qty_six"] = cow["goods"][8]["MILK"] == 6
checks["cow_first_production_pending_care_is_one"] = cow["state_by_day"][8]["pending_care_bonus"] == 1
checks["cow_first_production_state_qty_matches"] = cow["state_by_day"][8]["yield_units"] == 6
checks["normal_cow_no_model_conflicts"] = not cow["unsupported_by_day"]
milk_job = next(s for s in cow["services"][8] if s["op"] == "HARVEST")
milk_place = next(s for s in cow["services"][8] if s["op"] == "PLACE" and s["item"] == "MILK")
checks["milk_delivery_requires_harvest_origin"] = milk_place["dependencies"] == [milk_job["service_id"]] and milk_place["requires"] == {"MILK": 6}
checks["milk_and_fertilizer_two_separate_place_goods"] = {s["item"] for s in cow["services"][8] if s["op"] == "PLACE"} == {"MILK", "FERTILIZER"}

tomato = enrich(plant("TOMATO"))
checks["ongoing_has_four_product_rounds"] = [d for d, goods in tomato["goods"].items() if goods.get("TOMATO")] == [8, 9, 10, 11]
checks["ongoing_last_lifespan_rule"] = tomato["state_by_day"][11]["max_lifespan_step"] == 288
checks["normal_ongoing_no_model_conflicts"] = not tomato["unsupported_by_day"]
melon = enrich(plant("MELON"))
harvest_day = next(d for d, goods in melon["goods"].items() if goods.get("MELON"))
water = next(s for s in melon["services"][harvest_day] if s["op"] == "WATER")
harvest = next(s for s in melon["services"][harvest_day] if s["op"] == "HARVEST")
checks["terminal_crop_harvest_depends_on_water"] = harvest["dependencies"] == [water["service_id"]]
checks["terminal_crop_absent_next_day"] = melon["state_by_day"][harvest_day + 1] is None
checks["terminal_crop_no_future_services"] = not any(v for d, v in melon["services"].items() if d > harvest_day)

def problem(cals, day=8, current=0, shed=None, reserve=None, buy=0, fallback=None):
    return compiler.compile_day_problem(cals, day, current, shed or {"WHEAT": 3}, reserve or {"WHEAT": 3, "FERTILIZER": 12},
        {"qty": buy, "estimated_cash": 27 * buy, "order_hour": 0, "available_from_hour": 1},
        sum(c["work"].get(day, 0) for c in cals), 376, startup_fallback_days=fallback)

base = problem([cow]); checks["normal_cow_problem_supported"] = base["status"] == "SUPPORTED"
checks["current_day_legacy"] = "CURRENT_DAY_LEGACY" in problem([cow], 8, 8)["unsupported_reasons"]
checks["duplicate_asset_rejected"] = "DUPLICATE_ASSET_CALENDAR" in problem([cow, cow])["unsupported_reasons"]
other = enrich(animal("SHEEP"), pos=(3, 4))
checks["same_position_two_assets_rejected"] = "DUPLICATE_ACTIVE_POSITION" in problem([cow, other])["unsupported_reasons"]
checks["startup_day_fallback"] = "UNSUPPORTED_STARTUP_FRONTIER" in problem([cow], fallback=[8])["unsupported_reasons"]
checks["startup_fallback_not_all_future_days"] = problem([cow], 9, fallback=[8])["status"] == "SUPPORTED"
many = [enrich(animal("COW"), pos=(i % 10, i // 10)) for i in range(17)]
checks["feed_seventeen_falls_back"] = "FEED_OR_BUY_ABOVE_STAGE_B_16_LIMIT" in problem(many, shed={"WHEAT": 20})["unsupported_reasons"]
checks["buy_seventeen_falls_back"] = "FEED_OR_BUY_ABOVE_STAGE_B_16_LIMIT" in problem([cow], buy=17)["unsupported_reasons"]
bad_shed = compiler.compile_day_problem([cow], 8, 0, {}, {}, {"qty": 0, "estimated_cash": 0, "order_hour": 0, "available_from_hour": 1}, 10, 376)
checks["missing_feed_source_rejected"] = "CONDITIONAL_WHEAT_SOURCE_SHORTFALL" in bad_shed["unsupported_reasons"]
checks["overfull_shed_rejected"] = "START_SHED_OVER_CAPACITY" in problem([cow], shed={"WHEAT": 101})["unsupported_reasons"]
checks["fertilizer_reserve_above_twelve_rejected"] = "FERTILIZER_RESERVE_ABOVE_LEGACY_CAP" in problem([cow], reserve={"FERTILIZER": 13})["unsupported_reasons"]
end = problem([cow], 29)
checks["last_day_h22_only"] = end["end_hour"] == 22 and all(s["deadline"] <= 22 for s in end["services"])
checks["goods_from_field_services_exact"] = sum(s["gives"].get("MILK", 0) for s in base["services"]) == base["expected_goods"]["MILK"]
before = compiler.canonical_sha(cow); problem([cow]); checks["compile_does_not_mutate_calendar"] = compiler.canonical_sha(cow) == before

examples = {"cow_day8": base, "six_melon_water_day2": problem([enrich(plant("MELON"), pos=p) for p in ((3,4),(3,3),(3,2),(3,1),(2,1),(1,1))], 2)}
(HERE / "compiler_examples.json").write_text(json.dumps(examples, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
result = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
          "passed": sum(checks.values()), "total": len(checks), "legacy_comparisons": comparisons,
          "isolated_legacy_function_calls": legacy_calls, "enriched_calendar_calls": enriched_calls,
          "whole_candidate_calls": 0, "official_calls": 0, "new_complete_matches": 0,
          "compiler_sha256": sha(HERE / "calendar_compiler.py"), "test_sha256": sha(Path(__file__)),
          "parent_sha256": sha(PARENT), "schema_sha256": sha(HERE / "SCHEMA.md")}
path = HERE / ("compiler_tests_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
print(json.dumps({"result": str(path), "passed": result["passed"], "total": result["total"],
                  "failed": [k for k, v in checks.items() if not v], "examples": str(HERE / "compiler_examples.json")}, ensure_ascii=False))
