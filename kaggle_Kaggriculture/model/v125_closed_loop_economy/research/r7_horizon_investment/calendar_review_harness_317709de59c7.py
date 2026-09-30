"""独立只读日历微测；只调候选日历及官方局部规则，不调用完整比赛。"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import types


HERE = Path(__file__).resolve().parent
RULES_PATH = HERE.parent / "procurement_audit/rules_snapshot/kaggriculture.py"
RULES_SHA = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_source(path, name):
    data = path.read_bytes()
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module, digest(data)


def single_farm(tile, position=(4, 4)):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    x, y = position
    tiles[y][x] = deepcopy(tile)
    farm = {"farmer": list(position), "hands": [], "hires_today": 0, "money": 0,
            "unlocked_quadrants": ["NW", "NE", "SW", "SE"], "tiles": tiles}
    private = {"shed": {}, "inventories": [{"WHEAT": 100}], "seeds": {}}
    return farm, private


def normalized_goods(goods):
    return {int(d): {p: int(n) for p, n in g.items() if n} for d, g in goods.items() if any(g.values())}


def official_calendar(rules, initial, start_day):
    """控制每日充分水/粮和及时采收；不是可执行的工人排程或销售轨迹。"""
    farm, private = single_farm(initial)
    goods, feed, trace = {}, Counter(), []

    def action(day, command):
        before = deepcopy(private["inventories"][0])
        rules._apply_unit_action(farm, private, 0, command, 10, day, 24, 100)
        after = private["inventories"][0]
        for item in rules.PRODUCTS:
            delta = after.get(item, 0) - before.get(item, 0)
            if delta > 0:
                goods.setdefault(day, Counter())[item] += delta
        if command[0] == "FEED":
            feed[day] += before.get("WHEAT", 0) - after.get("WHEAT", 0)

    for day in range(start_day, 30):
        tile = farm["tiles"][4][4]
        if not isinstance(tile, dict) or not ("animal" in tile or tile.get("kind") == "PLANT"):
            break
        before = deepcopy(tile)
        if "animal" in tile:
            if tile.get("yield_units", 0):
                action(day, ["HARVEST"])
            if tile.get("fertilizer_available"):
                action(day, ["COLLECT_FERTILIZER"])
            if day < 29:
                if not tile.get("fed_today"):
                    action(day, ["FEED"])
                if day < 28 and not tile.get("cared_today"):
                    action(day, ["CARE"])
                rules._daily_refresh_animals(farm, day)
        else:
            # 每天多浇非增产日不会增加产品；增产由官方 WATER 自己决定。
            # day29 只给一次性作物的当场增产浇水，不凭空执行日终。
            spec = rules.CROPS[tile["crop"]]
            if not tile.get("watered_today") and (day < 29 or not spec["ongoing"]):
                action(day, ["WATER"])
            age = day - tile["planted_day"]
            if tile.get("yield_units", 0) and age >= spec["first_yield_day"]:
                if spec["ongoing"] or tile["yield_units"] >= spec["max_yield"] or age >= spec["max_yield_day"] or day == 29:
                    action(day, ["HARVEST"])
            if day < 29:
                rules._daily_refresh_plants(farm, day, 24)
        trace.append({"day": day, "before": before, "after_refresh": deepcopy(farm["tiles"][4][4]),
                      "collected_today": dict(goods.get(day, {}))})
    return {"goods": normalized_goods(goods), "feed": {d: n for d, n in feed.items() if n}, "trace": trace}


def terminal_delivery(rules, tile, position, hour):
    """只控制最后几帧的 HARVEST→移动→PLACE→SELL，不调用 interpreter。"""
    farm, private = single_farm(tile, position)
    private["inventories"] = [{}]
    market = rules._new_market()
    targets = ((4, 4), (5, 4), (4, 5), (5, 5))
    target = min(targets, key=lambda p: (abs(p[0] - position[0]) + abs(p[1] - position[1]), p))
    commands = [["HARVEST"]]
    x, y = position
    while x != target[0]:
        commands.append(["EAST" if x < target[0] else "WEST"])
        x += 1 if x < target[0] else -1
    while y != target[1]:
        commands.append(["SOUTH" if y < target[1] else "NORTH"])
        y += 1 if y < target[1] else -1
    commands.append(["PLACE", "MILK", 1])
    events, sold = [], 0
    for offset, command in enumerate(commands):
        h = hour + offset
        if h > 22:
            break
        rules._apply_unit_action(farm, private, 0, command, 10, 29, 24, 100)
        accepted = False
        if private["shed"].get("MILK", 0):
            price = rules.market_price("MILK", market["inventory"]["MILK"], market.get("params"))
            accepted = rules._commit_unit("SELL", "MILK", price, farm, private, market, 100)
            sold += int(accepted)
        events.append({"step": 29 * 24 + h, "hour": h, "action": command, "sale_accepted": accepted,
                       "position": list(farm["farmer"]), "inventory": deepcopy(private["inventories"][0])})
    return {"sold_units": sold, "cash": farm["money"], "events": events,
            "last_required_hour": hour + len(commands) - 1}


def run(candidate_path):
    rules, rules_sha = load_source(RULES_PATH, "calendar_review_rules")
    assert rules_sha == RULES_SHA
    candidate, candidate_sha = load_source(candidate_path, "calendar_review_candidate")
    cases, checks, differences = {}, {}, []

    def check(name, condition, actual=None, expected=None, category="required"):
        checks[name] = {"pass": bool(condition), "category": category, "actual": actual, "expected": expected}
        if not condition:
            differences.append({"check": name, **checks[name]})

    def compare(name, tile, day):
        model = candidate.project_calendar(deepcopy(tile), day, 0, (4, 4))
        actual = official_calendar(rules, tile, day)
        mg, og = normalized_goods(model["goods"]), actual["goods"]
        check(name + ":dated_goods", mg == og, mg, og)
        check(name + ":feed", {d: n for d, n in model["feed"].items() if n} == actual["feed"], model["feed"], actual["feed"])
        cases[name] = {"initial_tile": tile, "start_day": day, "model": model, "official_control": actual}
        return model, actual

    for animal, first_day, first_units in (("GOOSE", 4, 4), ("COW", 8, 6), ("SHEEP", 6, 6)):
        model, actual = compare("animal_fresh_" + animal, rules._new_animal(animal, 0), 0)
        item = rules.ANIMALS[animal]["product"]
        primary = {d: g[item] for d, g in actual["goods"].items() if item in g}
        check("animal_fresh_" + animal + ":first_day", min(primary) == first_day, min(primary), first_day)
        check("animal_fresh_" + animal + ":first_cap", primary[first_day] == first_units, primary[first_day], first_units)

    for already_cared in (False, True):
        tile = rules._new_animal("COW", 0)
        tile.update(pending_care_bonus=2, yield_units=5, fertilizer_available=True,
                    fed_today=already_cared, cared_today=already_cared)
        model, actual = compare("cow_pending_" + str(already_cared), tile, 7)
        check("cow_pending_" + str(already_cared) + ":old_bonus_first", actual["goods"][8]["MILK"] == 3,
              actual["goods"][8]["MILK"], 3)
        check("cow_pending_" + str(already_cared) + ":today_care_next", actual["goods"][10]["MILK"] == 3,
              actual["goods"][10]["MILK"], 3)
        check("cow_pending_" + str(already_cared) + ":existing_stock_once", actual["goods"][7]["MILK"] == 5,
              actual["goods"][7]["MILK"], 5)

    tile = rules._new_animal("COW", 0)
    tile["pending_care_bonus"] = 10
    model, actual = compare("cow_pending_cap", tile, 7)
    check("cow_pending_cap:official_max6", actual["goods"][8]["MILK"] == 6, actual["goods"][8]["MILK"], 6)

    for crop, expected_total in (("WHEAT", 4), ("CARROT", 3), ("MELON", 6)):
        tile = rules._new_plant(crop, 0, 24)
        model, actual = compare("annual_fresh_" + crop, tile, 0)
        total = sum(g.get(crop, 0) for g in actual["goods"].values())
        check("annual_fresh_" + crop + ":total", total == expected_total, total, expected_total)
        spec = rules.CROPS[crop]
        window = (spec["max_yield_day"] + 1) // 2
        for age in sorted({window - 1, window, spec["max_yield_day"], spec["max_yield_day"] + 1}):
            for fertilized in (False, True):
                t = rules._new_plant(crop, 0, 24)
                t.update(consecutive_unwatered=0, fertilized_until_day=age + 2 if fertilized else -1)
                farm, private = single_farm(t)
                rules._apply_unit_action(farm, private, 0, ["WATER"], 10, age, 24, 100)
                gained = farm["tiles"][4][4]["yield_units"] - 1
                expected = (2 if fertilized else 1) if window <= age <= spec["max_yield_day"] else 0
                check(f"water_window:{crop}:{age}:{fertilized}", gained == expected, gained, expected, "official_rule_control")
                # 使用同一个起始可见状态，比较候选完整余下日历。
                compare(f"annual_window_{crop}_{age}_{fertilized}", t, age)

    for crop, first, interval in (("TOMATO", 8, 1), ("STRAWBERRY", 10, 2)):
        tile = rules._new_plant(crop, 0, 24)
        model, actual = compare("ongoing_fresh_" + crop, tile, 0)
        primary = {d: g[crop] for d, g in actual["goods"].items() if crop in g}
        expected = {first + k * interval: 1 for k in range(4)}
        check("ongoing_fresh_" + crop + ":four_rounds", primary == expected, primary, expected)
        tile = rules._new_plant(crop, 0, 24)
        tile.update(consecutive_unwatered=0, fertilized_until_day=first + 1)
        compare("ongoing_fert_expiry_" + crop, tile, first - 1)
        tile = rules._new_plant(crop, 0, 24)
        tile.update(consecutive_unwatered=0, yield_units=4, fertilized_until_day=first + 2)
        compare("ongoing_existing_full_" + crop, tile, first)
        # 不采收的另一控制路径仅验证官方截断，不能拿它与及时采收模型混比。
        farm, private = single_farm(tile)
        rules._apply_unit_action(farm, private, 0, ["WATER"], 10, first, 24, 100)
        rules._daily_refresh_plants(farm, first, 24)
        check("ongoing_held_cap_" + crop, farm["tiles"][4][4]["yield_units"] == 4,
              farm["tiles"][4][4]["yield_units"], 4, "official_rule_control")

    for position, hour in (((4, 4), 20), ((4, 4), 21), ((4, 4), 22),
                           ((3, 4), 19), ((3, 4), 20), ((3, 4), 21), ((2, 4), 19)):
        tile = rules._new_animal("COW", 0)
        tile.update(yield_units=1, fed_today=True, cared_today=True)
        name = f"terminal_{position[0]}_{position[1]}_h{hour}"
        model = candidate.project_calendar(deepcopy(tile), 29, hour, position)
        actual = terminal_delivery(rules, tile, position, hour)
        credited = model["goods"].get(29, {}).get("MILK", 0)
        check(name + ":no_overcredit", credited <= actual["sold_units"], credited, actual["sold_units"])
        check(name + ":exact_window", credited == actual["sold_units"], credited, actual["sold_units"], "conservative_boundary_difference")
        check(name + ":no_step_after718", all(e["step"] <= 718 for e in actual["events"]),
              [e["step"] for e in actual["events"]], "<=718", "official_rule_control")
        cases[name] = {"initial_tile": tile, "position": position, "hour": hour,
                       "model": model, "official_short_actions": actual}

    required = {k: v for k, v in checks.items() if v["category"] != "conservative_boundary_difference"}
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(), "candidate_path": str(candidate_path),
            "candidate_sha256": candidate_sha, "rules_path": str(RULES_PATH), "rules_sha256": rules_sha,
            "harness_sha256": digest(Path(__file__).read_bytes()), "checks": checks, "differences": differences,
            "required_pass": all(v["pass"] for v in required.values()),
            "exact_all_pass": all(v["pass"] for v in checks.values()),
            "case_count": len(cases), "check_count": len(checks), "cases": cases,
            "scope": {"candidate_agent_calls": 0, "interpreter_calls": 0, "full_games": 0, "new_replay_reads": 0,
                      "meaning": "日历产量对照人工保证水粮、照护和及时采收，不验证全场劳力、路由、现金或销售；终局另用单资产短动作控制验证出售。",
                      "terminal_boundary": "exact_window 差异单独保留；若只低估可达窗口可视为保守模型边界，超记不可出售产品则 required 失败。"}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=HERE / "main.py")
    args = parser.parse_args()
    result = run(args.candidate.resolve())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = HERE / f"calendar_review_{result['candidate_sha256'][:12]}_{stamp}.json"
    # 每次写独立结果；不覆盖旧差异或已有审计文件。
    with output.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(output), "candidate_sha256": result["candidate_sha256"],
                      "case_count": result["case_count"], "check_count": result["check_count"],
                      "required_pass": result["required_pass"], "exact_all_pass": result["exact_all_pass"],
                      "differences": result["differences"]}, ensure_ascii=False, indent=2))
