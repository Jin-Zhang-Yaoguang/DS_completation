"""B 有界人工官方控制。须提供事先冻结的依赖清单；不导入完整候选。

执行：python test_official_controls.py --freeze FILE --output NEW_DIRECTORY
本文件导入无运行效果。生成器失败保留 PENDING；checker/官方首差停止并保存。
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import importlib
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / ".venv").is_dir())
RULE_PATH = ROOT / ".venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py"
SEED = 1250501
PASS = {"farmer": ["PASS"], "hands": [], "market": []}
ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plain(stock):
    return dict(sorted((k, v) for k, v in stock.items() if v))


def diff(after, before):
    return {k: after.get(k, 0) - before.get(k, 0) for k in sorted(set(after) | set(before)) if after.get(k, 0) != before.get(k, 0)}


def state_snapshot(env, seat):
    obs = env.state[seat].observation
    return deepcopy({"step": obs.step, "day": obs.day, "hour": obs.hour,
                     "farm": env.state[0].observation.farms[seat], "private": obs.private,
                     "market": env.state[0].observation.market, "town": env.state[0].observation.town,
                     "status": [s.status for s in env.state], "rewards": [s.reward for s in env.state]})


def compact(env, seat):
    snap = state_snapshot(env, seat)
    snap["farm"]["tiles"] = [{"pos": [x, y], "tile": t} for y, line in enumerate(snap["farm"]["tiles"]) for x, t in enumerate(line) if isinstance(t, dict)]
    return snap


class Observer:
    """透明调用原 helper 一次，记录逐原子物量；退出时恢复，不修改源码。"""
    def __init__(self, rules, env, seat):
        self.rules, self.env, self.seat = rules, env, seat
        self.unit_events, self.market_events, self.hire_events, self.eod_events = [], [], [], []
        self.originals = {}

    def __enter__(self):
        r = self.rules
        for name in ("_apply_unit_action", "_commit_unit", "_do_hire", "_end_of_day"):
            self.originals[name] = getattr(r, name)

        def unit(farm, private, idx, action, *args, **kwargs):
            watched = farm is self.env.state[0].observation.farms[self.seat]
            before = self.unit_snapshot(farm, private, idx) if watched else None
            ret = self.originals["_apply_unit_action"](farm, private, idx, action, *args, **kwargs)
            if watched:
                after = self.unit_snapshot(farm, private, idx)
                self.unit_events.append({"step": self.env.state[0].observation.step, "unit": idx, "action": deepcopy(action),
                                         "before": before, "after": after,
                                         "inventory_delta": diff(after["inventory"], before["inventory"]),
                                         "shed_delta": diff(after["shed"], before["shed"])})
            return ret

        def commit(op, item, price, farm, private, market, *args, **kwargs):
            watched = farm is self.env.state[0].observation.farms[self.seat]
            before = {"cash": farm["money"], "shed": deepcopy(private["shed"])} if watched else None
            ret = self.originals["_commit_unit"](op, item, price, farm, private, market, *args, **kwargs)
            if watched:
                self.market_events.append({"step": self.env.state[0].observation.step, "op": op, "item": item, "price": price,
                                           "actual_commit": bool(ret), "cash_delta": farm["money"] - before["cash"],
                                           "shed_delta": diff(private["shed"], before["shed"])})
            return ret

        def hire(farm, private, *args, **kwargs):
            watched = farm is self.env.state[0].observation.farms[self.seat]
            before = {"cash": farm["money"], "positions": deepcopy([farm["farmer"], *farm["hands"]]), "hires": farm["hires_today"]} if watched else None
            ret = self.originals["_do_hire"](farm, private, *args, **kwargs)
            if watched:
                self.hire_events.append({"step": self.env.state[0].observation.step, "before": before,
                    "cash_cost": before["cash"] - farm["money"], "actual_hired": farm["hires_today"] - before["hires"],
                    "after_positions": deepcopy([farm["farmer"], *farm["hands"]]),
                    "spawn": deepcopy(farm["hands"][-1]) if farm["hires_today"] > before["hires"] else None})
            return ret

        def eod(state, env, day):
            before = state_snapshot(env, self.seat)
            ret = self.originals["_end_of_day"](state, env, day)
            after = state_snapshot(env, self.seat)
            moved = Counter(after["private"]["shed"])
            moved.subtract(before["private"]["shed"])
            carried = Counter()
            for inv in before["private"]["inventories"]:
                carried.update(inv)
            lost = carried.copy(); lost.subtract(moved)
            self.eod_events.append({"day": day, "pre_eod": before, "post_eod": after,
                                    "automatic_deposit": plain(moved), "discarded": plain(lost)})
            return ret

        r._apply_unit_action, r._commit_unit, r._do_hire, r._end_of_day = unit, commit, hire, eod
        return self

    def unit_snapshot(self, farm, private, idx):
        pos = deepcopy(farm["farmer"] if idx == 0 else farm["hands"][idx - 1] if idx <= len(farm["hands"]) else None)
        inv = deepcopy(private["inventories"][idx]) if idx < len(private["inventories"]) else {}
        tile = deepcopy(farm["tiles"][pos[1]][pos[0]]) if pos else None
        return {"position": pos, "inventory": inv, "shed": deepcopy(private["shed"]), "tile": tile}

    def __exit__(self, *args):
        for name, fn in self.originals.items():
            setattr(self.rules, name, fn)


class Suite:
    def __init__(self, output, frozen):
        self.out, self.frozen = output, frozen
        self.counts = Counter()
        self.results, self.pending = [], []
        self.fx = load(HERE / "official_fixtures.py", "stage_b_official_fixtures")
        self.compiler = load(HERE / "calendar_compiler.py", "stage_b_compiler_for_official_control")
        self.scheduler = load(HERE / "scheduler.py", "stage_b_scheduler_for_official_control")
        self.checker = load(HERE / "checker.py", "stage_b_checker_for_official_control")
        self.rules = importlib.import_module("kaggle_environments.envs.kaggriculture.kaggriculture")
        self.make = importlib.import_module("kaggle_environments").make
        self.active = None

    def check(self, label, condition, detail=None):
        self.active.setdefault("checks", {})[label] = bool(condition)
        if not condition:
            self.active["first_failure"] = {"check": label, "detail": deepcopy(detail)}
            raise AssertionError(f"{self.active['id']}: {label}: {detail}")

    def start(self, case_id, seat, mode):
        self.active = {"id": case_id, "seat": seat, "mode": mode, "checks": {}, "rows": []}

    def save(self):
        if not self.active:
            return
        filename = self.active["id"] + (f"_s{self.active['seat']}" if self.active["seat"] is not None else "") + ".json.gz"
        with gzip.open(self.out / filename, "wt", encoding="utf-8") as f:
            json.dump(self.active, f, ensure_ascii=False, allow_nan=False)
        self.results.append({"id": self.active["id"], "seat": self.active["seat"], "mode": self.active["mode"],
                             "checks": self.active["checks"], "pending": self.active.get("pending"),
                             "path": str(self.out / filename), "sha256": sha(self.out / filename)})
        self.active = None

    def env(self, case, seat):
        self.counts["official_make_calls"] += 1
        original_initialize = self.rules._initialize

        def initialize(*args, **kwargs):
            self.counts["official_initialize_helper_calls"] += 1
            return original_initialize(*args, **kwargs)

        self.rules._initialize = initialize
        try:
            env = self.make("kaggriculture", configuration={"seed": SEED, "episodeSteps": 720, "weedSpawnChance": 0}, debug=False)
            self.counts["official_explicit_reset_calls"] += 1
            env.reset(2)
        finally:
            self.rules._initialize = original_initialize
        day, hour = case["day"], case.get("hour", 0)
        for s in env.state:
            s.observation.step = day * 24 + hour
            s.observation.day, s.observation.hour = day, hour
            s.status, s.reward = "ACTIVE", 0
        f = env.state[0].observation.farms[seat]
        positions = deepcopy(case.get("positions", [[4, 4]]))
        f["farmer"], f["hands"] = positions[0], positions[1:]
        f["money"], f["hires_today"] = 100000, len(positions) - 1
        f["tiles"] = [[None if x < 5 and y < 5 else "LOCKED" for x in range(10)] for y in range(10)]
        for row in case.get("tiles", []):
            x, y = row["pos"]; f["tiles"][y][x] = deepcopy(row["tile"])
        private = env.state[seat].observation.private
        private["inventories"] = deepcopy(case.get("inventories", [{} for _ in positions]))
        private["shed"], private["seeds"] = deepcopy(case.get("shed", {})), {}
        return env

    def step(self, env, seat, action):
        before = compact(env, seat)
        pair = [deepcopy(PASS), deepcopy(PASS)]; pair[seat] = deepcopy(action)
        for s, a in zip(env.state, pair):
            s.action = a
        self.counts["official_short_steps"] += 1
        env.state = self.rules.interpreter(env.state, env)
        for s in env.state:
            s.observation.step = before["step"] + 1
        self.active["rows"].append({"before": before, "action": deepcopy(action), "after": compact(env, seat)})

    def attach(self, obs, env, seat):
        self.active["unit_events"], self.active["market_events"] = obs.unit_events, obs.market_events
        self.active["hire_events"], self.active["eod_events"] = obs.hire_events, obs.eod_events
        self.active["final"] = state_snapshot(env, seat)

    def problem(self, case):
        calendars = []
        for tile in case["tiles"]:
            self.counts["calendar_calls"] += 1
            calendars.append(self.compiler.project_calendar_with_services(tile["tile"], case["day"], 0, tuple(tile["pos"]),
                             {"kind": "official_control_artificial_condition", "case": case["id"]}))
        self.active["input_calendars"] = calendars
        work = sum(c["work"].get(case["day"], 0) for c in calendars)
        n = case["n_hands"]
        hire = sum(self.rules._fib(i) for i in range(n))
        self.counts["compiler_calls"] += 1
        return self.compiler.compile_day_problem(calendars, case["day"], case["day"] - 1, case["shed"], case["reserve"],
            {"qty": case["buy"], "estimated_cash": case["buy"] * 30, "order_hour": 0, "available_from_hour": 1}, work, hire,
            conditional=[case["provenance"]])

    def certify(self, p, n):
        before = canonical(p)
        self.counts["scheduler_calls"] += 1
        cert = self.scheduler.schedule_day(p, n)
        self.check("scheduler_did_not_mutate_problem", canonical(p) == before)
        if cert["status"] != "FEASIBLE":
            self.active["pending"] = {"reason": "NO_CERTIFICATE_NOT_INFEASIBILITY_PROOF", "certificate": cert}
            self.pending.append(self.active["id"])
            return cert, None
        self.counts["checker_calls"] += 1
        check = self.checker.check_day(p, cert)
        self.check("independent_checker_valid", check["valid"], check)
        return cert, check

    def certificate_run(self, case, seat):
        self.start(case["id"], seat, "generated_certificate_official_day")
        p = self.problem(case)
        self.active["problem"] = p
        self.check("compiler_supported", p["status"] == "SUPPORTED", p["unsupported_reasons"])
        cert, checked = self.certify(p, case["n_hands"])
        self.active.update(certificate=cert, checker=checked, provenance=case["provenance"])
        if checked is None:
            self.save(); return
        actualcase = {"day": p["day"], "tiles": p["start_farm_tiles"], "shed": p["start_shed"]}
        env = self.env(actualcase, seat)
        self.active["initial"] = state_snapshot(env, seat)
        by_hour = {h: {} for h in range(p["end_hour"] + 1)}
        for entry in cert["actions"]:
            by_hour[entry["hour"]][entry["unit"]] = entry
        markets = {m["hour"]: m["orders"] for m in cert["markets"]}
        obs = Observer(self.rules, env, seat)
        with obs:
            try:
                for h in range(p["end_hour"] + 1):
                    units = by_hour[h]
                    f = env.state[0].observation.farms[seat]
                    self.check(f"actual_workers_h{h}", set(units) == set(range(len(f["hands"]) + 1)), {"declared": list(units), "actual_hands": f["hands"]})
                    action = {"farmer": units[0]["action"], "hands": [units[u]["action"] for u in range(1, len(units))], "market": markets[h]}
                    self.step(env, seat, action)
                self.verify_certificate(p, cert, checked, obs, env, seat)
            finally:
                self.attach(obs, env, seat)
        self.save()

    def verify_certificate(self, p, cert, checked, obs, env, seat):
        services = {s["service_id"]: s for s in p["services"]}
        progress, deliveries, harvested, consumed = Counter(), Counter(), Counter(), Counter()
        eventmap = {(e["step"] % 24, e["unit"]): e for e in obs.unit_events}
        receipts = []
        for a in cert["actions"]:
            e = eventmap[(a["hour"], a["unit"])]
            self.check(f"atomic_action_h{a['hour']}_u{a['unit']}", e["action"] == a["action"])
            allocations = a["service_allocations"]
            if not allocations:
                continue
            op = a["action"][0]
            if op == "PLACE":
                item = a["action"][1]
                actual = e["shed_delta"].get(item, 0)
                self.check(f"actual_place_h{a['hour']}_u{a['unit']}", actual == sum(x["qty"] for x in allocations), e)
                deliveries[item] += actual
            else:
                self.check(f"single_field_allocation_h{a['hour']}_u{a['unit']}", len(allocations) == 1 and allocations[0]["qty"] == 1)
                service = services[allocations[0]["service_id"]]
                before, after = e["before"]["tile"], e["after"]["tile"]
                self.check(f"field_position_{service['service_id']}", e["before"]["position"] == service["pos"])
                if op in ("WATER", "FEED", "CARE"):
                    flag = {"WATER": "watered_today", "FEED": "fed_today", "CARE": "cared_today"}[op]
                    actual = isinstance(before, dict) and not before.get(flag) and isinstance(after, dict) and after.get(flag) is True
                    self.check(f"field_actual_{service['service_id']}", actual, e)
                elif op == "COLLECT_FERTILIZER":
                    self.check(f"field_actual_{service['service_id']}", before.get("fertilizer_available") is True and after.get("fertilizer_available") is False, e)
                elif op == "HARVEST":
                    self.check(f"field_actual_{service['service_id']}", before.get("yield_units", 0) > 0 and (after is None or after.get("yield_units") == 0), e)
                expected_delta = Counter(service["gives"])
                expected_delta.subtract(service["requires"])
                self.check(f"field_material_{service['service_id']}", plain(expected_delta) == e["inventory_delta"], e)
                harvested.update(service["gives"]); consumed.update(service["requires"])
            for allocation in allocations:
                progress[allocation["service_id"]] += allocation["qty"]
                receipts.append({"service_id": allocation["service_id"], "actual_qty": allocation["qty"], "step": e["step"], "unit": e["unit"], "event_key": [a["hour"], a["unit"]]})
        self.active["actual_service_receipts"] = receipts
        self.check("all_actual_services_closed", dict(progress) == {sid: s["qty"] for sid, s in services.items()}, dict(progress))
        pre = obs.eod_events[-1]["pre_eod"] if obs.eod_events else state_snapshot(env, seat)
        pos = {str(i): x for i, x in enumerate([pre["farm"]["farmer"], *pre["farm"]["hands"]])}
        self.check("actual_pre_eod_terminal_positions", pos == cert["terminal_positions"], pos)
        stats = checked["stats"]
        self.check("checker_pre_eod_shed", plain(pre["private"]["shed"]) == stats["terminal_shed"], pre["private"]["shed"])
        self.check("checker_pre_eod_inventories", {str(i): plain(inv) for i, inv in enumerate(pre["private"]["inventories"])} == stats["terminal_inventories"])
        bought, sold = Counter(), Counter()
        costs, revenues = 0, 0
        for m in obs.market_events:
            if not m["actual_commit"]:
                continue
            if m["op"] == "BUY_PRODUCT": bought[m["item"]] += 1; costs += m["price"]
            if m["op"] == "SELL": sold[m["item"]] += 1; revenues += m["price"]
        hire = sum(h["cash_cost"] for h in obs.hire_events)
        self.check("official_fib_hire_cost", hire == cert["hire_cost"] == sum(self.rules._fib(i) for i in range(cert["n_hands"])))
        self.check("actual_cash_bridge", pre["farm"]["money"] == 100000 - hire - costs + revenues)
        for key, value in (("harvested_goods", harvested), ("delivered_goods", deliveries), ("consumed_goods", consumed), ("purchased_goods", bought), ("sold_goods", sold)):
            self.check("checker_" + key, stats[key] == plain(value), {"actual": plain(value), "checker": stats[key]})
        for h in obs.hire_events:
            occupancy = Counter(tuple(x) for x in h["before"]["positions"])
            expected = list(min(ACCESS, key=lambda q: (occupancy[q], ACCESS.index(q))))
            self.check(f"official_spawn_step{h['step']}_hire{h['before']['hires']}", h["actual_hired"] == 1 and h["spawn"] == expected, h)
        if p["day"] != 29:
            self.check("checker_post_eod_shed", stats["conditional_eod_shed"] == plain(env.state[seat].observation.private["shed"]))
            self.check("checker_eod_overflow", stats["conditional_eod_overflow"] == obs.eod_events[0]["discarded"])
            self.check("official_eod_worker_reset", env.state[0].observation.farms[seat]["farmer"] == [4, 4] and env.state[0].observation.farms[seat]["hands"] == [])
            for cal in self.active["input_calendars"]:
                x, y = cal["pos"]
                expected_tile = cal["state_by_day"][p["day"] + 1]
                actual_tile = env.state[0].observation.farms[seat]["tiles"][y][x]
                self.check("conditional_next_tile_vs_official_" + cal["asset_id"], actual_tile == expected_tile,
                           {"actual": actual_tile, "conditional_expected": expected_tile})
        else:
            self.check("terminal_h22_done_no_eod", env.done and not obs.eod_events and len(self.active["rows"]) == 23)
        self.active["actual_summary"] = {"harvested": plain(harvested), "delivered": plain(deliveries), "consumed": plain(consumed),
            "bought": plain(bought), "sold": plain(sold), "actual_buy_cost": costs, "actual_sell_revenue": revenues,
            "actual_hire_cost": hire, "final_cash": pre["farm"]["money"], "estimated_buy_cash_is_conditional": p["planned_wheat_buy"]["estimated_cash"]}

    def raw_run(self, case, seat):
        self.start(case["id"], seat, "artificial_short_rule_control_not_certificate")
        env = self.env(case, seat)
        self.active["initial"] = state_snapshot(env, seat)
        obs = Observer(self.rules, env, seat)
        with obs:
            try:
                for act in case["frames"]:
                    self.step(env, seat, act)
                self.verify_raw(case, obs, env, seat)
            finally:
                self.attach(obs, env, seat)
        self.save()

    def verify_raw(self, case, obs, env, seat):
        name = case["id"]
        inv = env.state[seat].observation.private["inventories"]
        shed = env.state[seat].observation.private["shed"]
        tiles = env.state[0].observation.farms[seat]["tiles"]
        rows = self.active["rows"]
        events = obs.unit_events
        if name == "hire_birth_after_actions":
            self.check("nine_h0_three_h1", Counter(h["step"] % 24 for h in obs.hire_events) == {0: 9, 1: 3})
            self.check("fib_twelve_376", sum(h["cash_cost"] for h in obs.hire_events) == 376)
            self.check("unit_actions_1_10_13", Counter(e["step"] % 24 for e in events) == {0: 1, 1: 10, 2: 13})
            for h in obs.hire_events:
                occ = Counter(tuple(x) for x in h["before"]["positions"])
                self.check(f"least_occupied_spawn_{h['before']['hires']}", h["spawn"] == list(min(ACCESS, key=lambda x: (occ[x], ACCESS.index(x)))))
            self.check("h1_moved_positions_used", obs.hire_events[9]["before"]["positions"] == [e["after"]["position"] for e in events if e["step"] % 24 == 1])
            self.check("bought_16", shed.get("WHEAT") == 16)
        elif name == "prebirth_hand_cannot_act":
            unborn = events[1]
            self.check("prebirth_no_position_no_effect", unborn["before"]["position"] is None and unborn["after"]["position"] is None)
            self.check("h1_born_hand_can_move", events[-1]["before"]["position"] == [5, 4] and events[-1]["after"]["position"] == [5, 3])
        elif name == "eleventh_market_order_ignored":
            self.check("only_first_ten_orders", len(obs.hire_events) == 10 and not obs.market_events and shed.get("WHEAT", 0) == 0)
        elif name == "buy_available_next_hour":
            self.check("h0_pickup_zero_h1_four", events[0]["inventory_delta"] == {} and events[1]["inventory_delta"] == {"WHEAT": 4})
        elif name == "shared_one_wheat_two_feeds":
            self.check("sequential_shared_pickup", events[0]["inventory_delta"] == {"WHEAT": 1} and events[1]["inventory_delta"] == {})
            self.check("only_first_animal_fed", tiles[3][4]["fed_today"] and not tiles[3][5]["fed_today"])
            self.check("only_one_wheat_consumed", sum(-e["inventory_delta"].get("WHEAT", 0) for e in events if e["action"][0] == "FEED") == 1)
        elif name == "same_animal_feed_twice":
            self.check("second_feed_no_consume", inv[0] == {"WHEAT": 1} and events[1]["inventory_delta"] == {})
        elif name == "place_one_product_at_a_time":
            self.check("milk_place_leaves_fertilizer", events[0]["after"]["inventory"] == {"FERTILIZER": 1} and events[0]["shed_delta"] == {"MILK": 2})
            self.check("two_distinct_placements", events[1]["shed_delta"] == {"FERTILIZER": 1} and not inv[0])
        elif name == "shared_warehouse_capacity":
            self.check("one_room_only_low_index", events[0]["shed_delta"] == {"MILK": 1} and events[1]["shed_delta"] == {})
            self.check("remaining_cargo_not_dropped", inv == [{"MILK": 1}, {"WOOL": 2}] and sum(shed.values()) == 100)
        elif name == "later_sell_cannot_preclear_place":
            self.check("place_only_one_despite_later_sale", events[0]["shed_delta"] == {"MILK": 1} and inv[0] == {"MILK": 1} and shed["WHEAT"] == 97)
        elif name == "pickup_frees_space_before_buy":
            self.check("pickup_then_four_real_buys", events[0]["inventory_delta"] == {"WHEAT": 4} and sum(m["actual_commit"] for m in obs.market_events) == 4 and shed["WHEAT"] == 100)
        elif name == "terminal_h22_place_sell":
            self.check("done_no_h23_eod", env.done and not obs.eod_events and env.state[seat].observation.step == 719)
            self.check("real_final_sell_two", sum(m["actual_commit"] for m in obs.market_events if m["op"] == "SELL") == 2 and env.state[0].observation.farms[seat]["money"] > 100000)
        elif name == "terminal_h22_remote_harvest":
            self.check("terminal_remote_not_deposited", env.done and not obs.eod_events and inv[0] == {"MILK": 2} and shed.get("MILK", 0) == 0)
            self.check("unstocked_sale_no_cash", env.state[0].observation.farms[seat]["money"] == 100000 and not any(m["actual_commit"] for m in obs.market_events))
        elif name == "fed_care_prior_bonus_eod":
            t = tiles[4][3]
            self.check("old_bonus_into_yield_new_bonus_pending", t["yield_units"] == 3 and t["pending_care_bonus"] == 1 and t["fed_today"] is False and t["cared_today"] is False)
        elif name == "unfed_care_no_bonus_eod":
            t = tiles[4][3]
            self.check("unfed_still_base_one_but_bonus_lost", t["yield_units"] == 1 and t["pending_care_bonus"] == 0 and t["consecutive_unfed"] == 1)
        elif name == "ongoing_fourth_production_lifespan":
            t = tiles[4][3]
            self.check("cap_four_new_expiry_day12", t["yield_units"] == 4 and t["max_lifespan_step"] == 288)
        elif name == "one_shot_harvest_destroys_asset":
            self.check("only_one_real_harvest", tiles[4][3] is None and inv[0] == {"MELON": 6} and events[1]["inventory_delta"] == events[2]["inventory_delta"] == {})
        elif name == "missed_care_kills_at_eod":
            self.check("crop_weed_animal_empty_pasture", tiles[4][3] == {"kind": "WEED"} and tiles[3][4] == {"kind": "PASTURE"})
        elif name == "eod_partial_drop_is_not_place":
            self.check("eod_deposit_one_discard_four", obs.eod_events[0]["automatic_deposit"] == {"MILK": 1} and obs.eod_events[0]["discarded"] == {"MILK": 1, "FERTILIZER": 1, "WOOL": 2})
            self.check("automatic_not_actual_place", not any(e["action"][0] == "PLACE" for e in events) and inv == [{}])
        elif name == "lifespan_last_frame_harvest_allowed":
            self.check("same_frame_harvest_precedes_decay", inv[0] == {"MELON": 1} and tiles[4][3] is None)
        elif name == "lifespan_move_too_late":
            self.check("decayed_before_next_harvest", tiles[4][3] == {"kind": "WEED"} and inv[0] == {})
        else:
            raise ValueError("missing test oracle " + name)

    def pure_checks(self):
        self.start("pure_repeat_rollback_and_fallback", None, "pure_calls_no_engine")
        case = self.fx.certificate_fixtures()[1]
        p = self.problem(case)
        c1, _ = self.certify(p, case["n_hands"])
        p0 = canonical(p)
        bad = deepcopy(p); bad["planned_wheat_buy"]["qty"] = 17
        self.counts["scheduler_calls"] += 1
        rejected = self.scheduler.schedule_day(bad, case["n_hands"])
        self.check("buy17_no_certificate", rejected["status"] == "NO_CERTIFICATE")
        c2, _ = self.certify(p, case["n_hands"])
        self.check("failure_does_not_pollute_later_schedule", canonical(p) == p0 and c1 == c2)
        unsupported = deepcopy(p); unsupported["status"] = "UNSUPPORTED"; unsupported["unsupported_reasons"] = ["UNSUPPORTED_STARTUP_FRONTIER"]
        self.counts["scheduler_calls"] += 1
        self.check("unsupported_never_feasible", self.scheduler.schedule_day(unsupported, 12)["status"] == "NO_CERTIFICATE")
        self.active["problem"], self.active["certificates"] = p, [c1, rejected, c2]
        self.save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output exists; preserve existing evidence")
    frozen_bytes = args.freeze.read_bytes()
    frozen = json.loads(frozen_bytes)
    needed = [Path(__file__).resolve(), HERE / "official_fixtures.py", HERE / "SCHEMA.md", HERE / "calendar_compiler.py", HERE / "scheduler.py", HERE / "checker.py", RULE_PATH]
    expected = {str(Path(k).resolve()): v for k, v in frozen["files"].items()}
    if frozen.get("schema") != "r10-stage-b-official-control-freeze-v1" or any(str(p) not in expected for p in needed):
        raise SystemExit("freeze missing required script/schema/runtime source")
    frozen_paths = [Path(path) for path in expected]
    for path in frozen_paths:
        if sha(path) != expected[str(path)]:
            raise SystemExit("freeze source drift: " + str(path))
    args.output.mkdir(parents=True)
    suite, failure = None, None
    try:
        suite = Suite(args.output, frozen)
        if sha(RULE_PATH) != suite.fx.RULES_SHA:
            raise RuntimeError("official rules differ from reviewed version")
        suite.pure_checks()
        for case in suite.fx.certificate_fixtures():
            for seat in (0, 1):
                suite.certificate_run(case, seat)
        for case in suite.fx.raw_fixtures():
            for seat in (0, 1):
                suite.raw_run(case, seat)
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        if suite:
            suite.save()
        drift = [str(p) for p in frozen_paths if sha(p) != expected[str(p)]]
        freeze_drift = args.freeze.read_bytes() != frozen_bytes
        if drift or freeze_drift:
            failure = {"type": "SOURCE_DRIFT", "paths": drift, "freeze_changed": freeze_drift, "earlier_failure": failure}
        counts = dict(suite.counts) if suite else {}
        counts.update(complete_candidate_calls=0, new_complete_matches=0, new_replays_opened=0)
        result = {"schema": "r10-stage-b-official-controls-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
                  "status": "ERROR" if failure else "PENDING" if suite.pending else "PASS",
                  "failure": failure, "counts": counts, "pending": suite.pending if suite else [],
                  "runs": suite.results if suite else [], "freeze_sha256": hashlib.sha256(frozen_bytes).hexdigest(),
                  "source_files": expected, "source_drift": drift,
                  "scope": "人工条件单日/短片段；逐原子原官方效果，非自然未来到达/强度/G1/G2/金牌证据。完整候选0，新完整游戏0。",
                  "fixture_configuration": {"seed": SEED, "seed_status": "previously opened artificial microfixture", "weedSpawnChance": 0, "starting_injected_cash": 100000}}
        (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print(json.dumps({k: result[k] for k in ("status", "counts", "pending", "failure")}, ensure_ascii=False))
    return int(bool(failure))


if __name__ == "__main__":
    raise SystemExit(main())
