"""独立手写路线与破坏性变异；不调用compiler/scheduler/candidate/官方引擎。"""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from datetime import datetime, timezone

from checker import check_day

RESULTS = []
SPAWNS = {0: [4, 4], 1: [5, 4], 2: [4, 5], 3: [5, 5], 4: [4, 4],
          5: [5, 4], 6: [4, 5], 7: [5, 5], 8: [4, 4], 9: [5, 4],
          10: [4, 5], 11: [5, 5], 12: [4, 4]}


def digest(p):
    return hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def empty(day=12):
    return {"schema": "r10-future-day-problem-v1", "status": "SUPPORTED", "unsupported_reasons": [],
            "day": day, "current_day": day - 1, "end_hour": 22 if day == 29 else 23,
            "board_size": 10, "start_farm_tiles": [], "start_shed": {}, "reserved_shed": {},
            "planned_wheat_buy": {"qty": 0, "estimated_cash": 0., "order_hour": 0, "available_from_hour": 1},
            "services": [], "expected_goods": {}, "feed_units": 0, "legacy_work": 0, "legacy_hire_cost": 0.,
            "conditional": [{"kind": "handwritten_fixture", "detail": "人工条件日初"}],
            "hire_protocol": {"max_hands": 12, "farmer_h0_pass": True, "h0_max_hires": 9, "h1_remaining_hires": True}, "capacity": 100}


def service(aid, op, pos, *, sid=None, gives=None, deps=None, qty=1, item=None, deadline=23):
    req = {"WHEAT": 1} if op == "FEED" else {item: qty} if op == "PLACE" else {}
    return {"service_id": sid or aid + "/" + op, "asset_id": aid, "pos": pos,
            "op": op, "item": item, "qty": qty, "release": 0, "deadline": deadline,
            "requires": req, "gives": gives or {}, "dependencies": deps or [], "splittable": op == "PLACE"}


def certificate(p, steps=None, hands=0, markets=None, terminal=None):
    steps = steps or {}
    rows = []
    for h in range(p["end_hour"] + 1):
        for u in range(hands + 1):
            birth = 0 if u == 0 else 1 if u <= 9 else 2
            if h < birth:
                continue
            a, alloc = steps.get((h, u), (["PASS"], []))
            rows.append({"hour": h, "unit": u, "action": a, "service_allocations": alloc})
    mk = {h: [] for h in range(p["end_hour"] + 1)}
    mk[0] = [["HIRE"] for _ in range(min(9, hands))]
    if p["planned_wheat_buy"]["qty"]:
        mk[0].append(["BUY_PRODUCT", "WHEAT", p["planned_wheat_buy"]["qty"]])
    mk[1] = [["HIRE"] for _ in range(max(0, hands - 9))]
    if markets:
        mk.update(markets)
    costs = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
    return {"schema": "r10-future-day-certificate-v1", "status": "FEASIBLE", "problem_sha256": digest(p),
            "n_hands": hands, "actions": rows, "markets": [{"hour": h, "orders": o} for h, o in sorted(mk.items())],
            "scheduled_service_ids": [s["service_id"] for s in p["services"]], "hire_cost": sum(costs[:hands]),
            "terminal_positions": terminal or {str(u): SPAWNS[u] for u in range(hands + 1)}, "reason": None}


def alloc(sid, qty=1):
    return [{"service_id": sid, "qty": qty}]


def animal_case():
    p = empty(); aid = "animal:COW:0:4,4"
    tile = {"kind": "PASTURE", "animal": "COW", "placed_day": 0, "yield_units": 2,
            "consecutive_unfed": 0, "pending_care_bonus": 0, "fed_today": False,
            "cared_today": False, "fertilizer_available": True}
    p["start_farm_tiles"] = [{"asset_id": aid, "pos": [4, 4], "tile": tile}]
    p["planned_wheat_buy"] = {"qty": 1, "estimated_cash": 27., "order_hour": 0, "available_from_hour": 1}
    p["feed_units"] = 1
    p["services"] = [service(aid, "FEED", [4, 4], sid="feed"), service(aid, "CARE", [4, 4], sid="care", deps=["feed"]),
                     service(aid, "COLLECT_FERTILIZER", [4, 4], sid="fert", gives={"FERTILIZER": 1}),
                     service(aid, "HARVEST", [4, 4], sid="milk", gives={"MILK": 2}),
                     service(aid, "PLACE", None, sid="fert_drop", qty=1, item="FERTILIZER", deps=["fert"]),
                     service(aid, "PLACE", None, sid="milk_drop", qty=2, item="MILK", deps=["milk"])]
    p["expected_goods"] = {"MILK": 2, "FERTILIZER": 1}
    steps = {(1, 0): (["PICKUP", "WHEAT", 1], []), (2, 0): (["FEED"], alloc("feed")),
             (3, 0): (["CARE"], alloc("care")), (4, 0): (["COLLECT_FERTILIZER"], alloc("fert")),
             (5, 0): (["HARVEST"], alloc("milk")), (6, 0): (["PLACE", "FERTILIZER", 1], alloc("fert_drop")),
             (7, 0): (["PLACE", "MILK", 2], alloc("milk_drop", 2))}
    return p, certificate(p, steps)


def crop_case(day=12, mls=-1):
    p = empty(day); aid = f"plant:MELON:{day-12}:3,4"
    tile = {"kind": "PLANT", "crop": "MELON", "planted_day": day-12, "yield_units": 1,
            "consecutive_unwatered": 1, "watered_today": False, "fertilized_until_day": -1, "max_lifespan_step": mls}
    p["start_farm_tiles"] = [{"asset_id": aid, "pos": [3, 4], "tile": tile}]
    end = p["end_hour"]
    p["services"] = [service(aid, "WATER", [3, 4], sid="water", deadline=end),
                     service(aid, "HARVEST", [3, 4], sid="harvest", gives={"MELON": 2}, deps=["water"], deadline=end),
                     service(aid, "PLACE", None, sid="drop", item="MELON", qty=2, deps=["harvest"], deadline=end)]
    p["expected_goods"] = {"MELON": 2}
    steps = {(1, 0): (["WEST"], []), (2, 0): (["WATER"], alloc("water")),
             (3, 0): (["HARVEST"], alloc("harvest")), (4, 0): (["EAST"], []),
             (5, 0): (["PLACE", "MELON", 2], alloc("drop", 2))}
    return p, certificate(p, steps)


def row(c, hour, unit=0):
    return next(r for r in c["actions"] if (r["hour"], r["unit"]) == (hour, unit))


class CheckerTests(unittest.TestCase):
    def verify(self, name, p, c, valid, code=None, refresh=True):
        if refresh:
            c["problem_sha256"] = digest(p)
        before = copy.deepcopy((p, c)); result = check_day(p, c)
        RESULTS.append({"name": name, "expected_valid": valid, "valid": result["valid"], "errors": result["errors"],
                        "resource_identity": result["stats"].get("resource_identity"), "unit_actions": result["stats"].get("unit_actions")})
        self.assertEqual((p, c), before, name + " mutated inputs")
        self.assertEqual(result["valid"], valid, (name, result))
        if code:
            self.assertEqual(result["errors"][0]["code"], code, (name, result))
        return result

    def test_empty_and_twelve_hands(self):
        p = empty(); self.verify("empty", p, certificate(p), True)
        p["planned_wheat_buy"].update(qty=16, estimated_cash=432.)
        r = self.verify("12hands_h0nine_h1three", p, certificate(p, hands=12), True)
        self.assertEqual(r["stats"]["hire_cost"], 376)
        self.assertEqual(r["stats"]["hires"][9]["spawn"], [4, 5])
        self.assertEqual(r["stats"]["hires"][9]["available_from_hour"], 2)

    def test_animal_service_and_cash_condition(self):
        p, c = animal_case(); r = self.verify("animal_all_services", p, c, True)
        self.assertEqual(r["stats"]["delivered_goods"], {"FERTILIZER": 1, "MILK": 2})
        self.assertEqual(r["stats"]["cash_feasibility"], "CONDITIONAL_EXTERNAL_FUNDING_CHECK")
        self.assertIsNone(r["stats"]["sales_cash"])
        p["reserved_shed"] = {"WHEAT": 1}
        self.verify("reserved_wheat_may_feed", p, c, True)

    def test_melon_water_growth_and_terminal(self):
        p, c = crop_case(); self.verify("melon_water_then_harvest", p, c, True)
        p, c = crop_case(29)
        row(c, 5).update(action=["PASS"], service_allocations=[])
        row(c, 22).update(action=["PLACE", "MELON", 2], service_allocations=alloc("drop", 2))
        self.verify("day29_h22_delivery", p, c, True)
        c["actions"].append({"hour": 23, "unit": 0, "action": ["PASS"], "service_allocations": []})
        self.verify("day29_h23_illegal", p, c, False, "ACTION_SLOT")

    def test_lifespan_boundary(self):
        p, c = crop_case(12, 12*24+3)
        for s in p["services"][:2]: s["deadline"] = 3
        self.verify("harvest_at_mls_before_decay", p, c, True)
        p["services"][1]["deadline"] = 4
        self.verify("deadline_beyond_mls", p, c, False, "LIFESPAN_DEADLINE")
        p, c = crop_case(12, 12*24-1)
        self.verify("already_expired", p, c, False, "EXPIRED_ASSET")

    def test_completion_and_dependency_mutations(self):
        for name, mutate in [
            ("missing_water_action", lambda p,c: row(c,2).update(action=["PASS"],service_allocations=[])),
            ("move_claims_water", lambda p,c: row(c,1).update(service_allocations=alloc("water"))),
            ("duplicate_water_action", lambda p,c: row(c,3).update(action=["WATER"],service_allocations=alloc("water"))),
            ("wrong_worker_location", lambda p,c: row(c,1).update(action=["PASS"])),
            ("wrong_harvest_amount", lambda p,c: p["services"][1]["gives"].update(MELON=3)),
            ("forged_complete_list", lambda p,c: c.update(scheduled_service_ids=[True])),
            ("fake_terminal", lambda p,c: c.update(terminal_positions={"0":[9,9]})),
            ("missed_deadline", lambda p,c: p["services"][0].update(deadline=1)),
            ("already_watered", lambda p,c: p["start_farm_tiles"][0]["tile"].update(watered_today=True)),
            ("locked_asset", lambda p,c: p["start_farm_tiles"][0].update(tile="LOCKED")),
            ("identity_birth_changed", lambda p,c: p["start_farm_tiles"][0]["tile"].update(planted_day=1)),
            ("dependency_cycle", lambda p,c: p["services"][0].update(dependencies=["drop"])),
        ]:
            with self.subTest(name=name):
                p,c=crop_case();mutate(p,c);self.verify(name,p,c,False)

    def test_hire_and_order_mutations(self):
        for name, mutate in [
            ("extra_prebirth_action", lambda p,c: c["actions"].insert(1,{"hour":0,"unit":1,"action":["PASS"],"service_allocations":[]})),
            ("h0_ten_hires", lambda p,c: c["markets"][0]["orders"].append(["HIRE"])),
            ("h1_newworker_early", lambda p,c: c["actions"].insert(11,{"hour":1,"unit":10,"action":["PASS"],"service_allocations":[]})),
            ("eleven_orders", lambda p,c: c["markets"][0]["orders"].extend([["SELL","MILK",1],["SELL","MILK",1]])),
            ("wrong_fib_total", lambda p,c: c.update(hire_cost=12)),
            ("fake_spawn_terminal", lambda p,c: c["terminal_positions"].update({"1":[3,4]})),
            ("missing_market_hour", lambda p,c: c["markets"].pop()),
            ("boolean_n_hands", lambda p,c: c.update(n_hands=True)),
        ]:
            with self.subTest(name=name):
                p=empty();c=certificate(p,hands=12);mutate(p,c);self.verify(name,p,c,False)

    def test_h1_spawn_uses_post_unit_positions(self):
        p=empty(); terminals={str(u):SPAWNS[u][:] for u in range(11)}
        terminals["0"]=[3,4];terminals["10"]=[4,4]
        c=certificate(p,{(1,0):(["WEST"],[])},hands=10,terminal=terminals)
        r=self.verify("h1_postmove_spawn",p,c,True)
        self.assertEqual(r["stats"]["hires"][9]["spawn"],[4,4])

    def test_material_capacity_and_source(self):
        for name, mutate in [
            ("no_pickup_feed", lambda p,c: row(c,1).update(action=["PASS"])),
            ("pickup_before_market_arrives", lambda p,c: row(c,0).update(action=["PICKUP","WHEAT",1])),
            ("double_feed", lambda p,c: row(c,3).update(action=["FEED"],service_allocations=alloc("feed"))),
            ("buy_17", lambda p,c: p["planned_wheat_buy"].update(qty=17)),
            ("feed_17", lambda p,c: p.update(feed_units=17)),
            ("pickup_five", lambda p,c: row(c,1).update(action=["PICKUP","WHEAT",5])),
            ("full_shed_blocks_buy", lambda p,c: p.update(start_shed={"TOMATO":100})),
            ("sell_reserved", lambda p,c: (p.update(start_shed={"TOMATO":3},reserved_shed={"TOMATO":3}),c["markets"][0]["orders"].append(["SELL","TOMATO",1]))),
            ("boolean_buy_qty", lambda p,c: c["markets"][0]["orders"][0].__setitem__(2,True)),
            ("negative_sell", lambda p,c: c["markets"][0]["orders"].append(["SELL","MILK",-1])),
            ("cross_item_place_merge", lambda p,c: row(c,6).update(service_allocations=alloc("milk_drop"))),
            ("duplicate_delivery_alloc", lambda p,c: row(c,7).update(service_allocations=alloc("milk_drop")+alloc("milk_drop"))),
        ]:
            with self.subTest(name=name):
                p,c=animal_case();mutate(p,c);self.verify(name,p,c,False)
        p,c=animal_case();p["start_shed"]={"MILK":2}
        row(c,5).update(action=["PICKUP","MILK",2],service_allocations=[])
        self.verify("existing_milk_cannot_fake_harvest",p,c,False)
        p,c=animal_case();p["start_shed"]={"TOMATO":99}
        c["markets"][6]["orders"]=[["SELL","TOMATO",99]]
        self.verify("market_sale_after_unit_place",p,c,True)
        # 99 tomato + 1肥已满，milk PLACE发生后才SELL，不能借这笔释放仓容。
        c["markets"][6]["orders"]=[];c["markets"][7]["orders"]=[["SELL","TOMATO",99]]
        self.verify("same_hour_sale_cannot_preclear_place",p,c,False,"PLACE_ACTUAL_QUANTITY")

    def test_mutual_material_and_incomplete_eod(self):
        p,c=animal_case();p["planned_wheat_buy"].update(qty=0,estimated_cash=0.);p["start_shed"]={"WHEAT":1}
        c=certificate(p,hands=1)
        row(c,1,0).update(action=["PICKUP","WHEAT",1]);row(c,1,1).update(action=["PICKUP","WHEAT",1])
        self.verify("two_workers_one_grain",p,c,False,"PICKUP_PARTIAL")
        p,c=animal_case();row(c,7).update(action=["PASS"],service_allocations=[])
        self.verify("eod_auto_drop_not_delivery",p,c,False,"MISSING_SERVICE")

    def test_same_product_combined_delivery(self):
        p=empty();steps={}
        for i,pos in enumerate(([4,4],[5,4])):
            aid=f"animal:COW:0:{pos[0]},{pos[1]}"
            tile={"kind":"PASTURE","animal":"COW","placed_day":0,"yield_units":1,"consecutive_unfed":0,
                  "pending_care_bonus":0,"fed_today":True,"cared_today":True,"fertilizer_available":False}
            p["start_farm_tiles"].append({"asset_id":aid,"pos":pos,"tile":tile})
            p["services"].extend([service(aid,"HARVEST",pos,sid=f"h{i}",gives={"MILK":1}),
                                   service(aid,"PLACE",None,sid=f"p{i}",item="MILK",deps=[f"h{i}"])])
        p["expected_goods"]={"MILK":2}
        steps={(1,0):(["HARVEST"],alloc("h0")),(2,0):(["EAST"],[]),(3,0):(["HARVEST"],alloc("h1")),
               (4,0):(["PLACE","MILK",2],alloc("p0")+alloc("p1"))}
        c=certificate(p,steps,terminal={"0":[5,4]});self.verify("combined_same_product_two_sources",p,c,True)
        p["services"][3]["dependencies"]=["h0"]
        self.verify("same_source_double_spend",p,c,False,"DELIVERY_PROVENANCE")

    def test_partial_place_and_metadata(self):
        p,c=animal_case();row(c,7).update(action=["PLACE","MILK",9])
        self.verify("truthful_partial_place_qty",p,c,True)
        row(c,7).update(service_allocations=alloc("milk_drop",9))
        self.verify("requested_not_actual_place",p,c,False,"PLACE_ACTUAL_QUANTITY")
        for name,mutate in [("same_day_not_future",lambda p,c:p.update(current_day=12)),
                            ("unsupported_not_pass",lambda p,c:p.update(status="UNSUPPORTED",unsupported_reasons=["startup"])),
                            ("no_certificate_not_pass",lambda p,c:c.update(status="NO_CERTIFICATE")),
                            ("duplicate_asset",lambda p,c:p["start_farm_tiles"].append(copy.deepcopy(p["start_farm_tiles"][0]))),
                            ("missing_field_service",lambda p,c:p["services"].pop(3)),
                            ("wrong_hash",lambda p,c:c.update(problem_sha256="0"*64))]:
            p,c=animal_case();mutate(p,c);self.verify(name,p,c,False,refresh=name!="wrong_hash")

    def test_optional_terminal_state(self):
        p,c=animal_case();c.update(terminal_shed={"MILK":2,"FERTILIZER":1},
                                 terminal_inventories=[{}],remaining_service_quantities={})
        self.verify("optional_terminal_truth",p,c,True)
        for name,field,value in [("fake_shed","terminal_shed",{"MILK":3,"FERTILIZER":1}),
                                 ("fake_backpack","terminal_inventories",[{"MILK":1}]),
                                 ("fake_remaining","remaining_service_quantities",{"milk_drop":1})]:
            cc=copy.deepcopy(c);cc[field]=value;self.verify(name,p,cc,False)

    def test_split_delivery_across_workers(self):
        p=empty()
        for i,pos in enumerate(([4,4],[5,4])):
            aid=f"animal:COW:0:{pos[0]},{pos[1]}"
            tile={"kind":"PASTURE","animal":"COW","placed_day":0,"yield_units":1,"consecutive_unfed":0,
                  "pending_care_bonus":0,"fed_today":True,"cared_today":True,"fertilizer_available":False}
            p["start_farm_tiles"].append({"asset_id":aid,"pos":pos,"tile":tile})
            p["services"].append(service(aid,"HARVEST",pos,sid=f"h{i}",gives={"MILK":1}))
        p["services"].append(service(p["start_farm_tiles"][0]["asset_id"],"PLACE",None,sid="shared_drop",
                                     item="MILK",qty=2,deps=["h0","h1"]))
        p["expected_goods"]={"MILK":2}
        steps={(1,0):(["HARVEST"],alloc("h0")),(1,1):(["HARVEST"],alloc("h1")),
               (2,0):(["PLACE","MILK",1],alloc("shared_drop")),(2,1):(["PLACE","MILK",1],alloc("shared_drop"))}
        c=certificate(p,steps,hands=1);self.verify("split_delivery_two_workers",p,c,True)

    def test_eod_overflow_is_reported_not_free_delivery(self):
        p=empty();aid="animal:COW:0:4,4"
        tile={"kind":"PASTURE","animal":"COW","placed_day":0,"yield_units":4,"consecutive_unfed":0,
              "pending_care_bonus":0,"fed_today":True,"cared_today":True,"fertilizer_available":False}
        p["start_farm_tiles"]=[{"asset_id":aid,"pos":[4,4],"tile":tile}]
        p["start_shed"]={"TOMATO":96,"WHEAT":4};p["expected_goods"]={"MILK":4}
        p["services"]=[service(aid,"HARVEST",[4,4],sid="milk",gives={"MILK":4}),
                         service(aid,"PLACE",None,sid="drop",qty=4,item="MILK",deps=["milk"])]
        steps={(1,0):(["PICKUP","WHEAT",4],[]),(2,0):(["HARVEST"],alloc("milk")),
               (3,0):(["PLACE","MILK",4],alloc("drop",4))}
        r=self.verify("eod_unused_feed_overflow_explicit",p,certificate(p,steps),True)
        self.assertEqual(r["stats"]["conditional_eod_overflow"],{"WHEAT":4})
        self.assertEqual(r["stats"]["terminal_inventories"],{"0":{"WHEAT":4}})

    def test_buy_cash_condition_domain(self):
        p,c=animal_case();p["planned_wheat_buy"]["estimated_cash"]=0
        self.verify("positive_buy_zero_cash_rejected",p,c,False,"BUY_CASH")
        p,c=animal_case();p["planned_wheat_buy"]["estimated_cash"]=float("nan")
        self.verify("nonfinite_buy_cash_rejected",p,c,False,"BUY_PROTOCOL",refresh=False)
        p=empty();p["planned_wheat_buy"]["estimated_cash"]=1
        self.verify("zero_buy_nonzero_cash_rejected",p,certificate(p),False,"BUY_CASH")


if __name__ == "__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CheckerTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    here=Path(__file__).resolve().parent
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out={"schema":"r10-b-checker-handwritten-tests-v1","created_utc":stamp,
         "checker_sha256":hashlib.sha256((here/"checker.py").read_bytes()).hexdigest(),
         "harness_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         "schema_sha256":hashlib.sha256((here/"SCHEMA.md").read_bytes()).hexdigest(),
         "test_methods":result.testsRun,"cases":RESULTS,"case_count":len(RESULTS),
         "success":result.wasSuccessful(),"failures":len(result.failures),"errors":len(result.errors),
         "candidate_calls":0,"engine_calls":0,"generator_calls":0,"compiler_calls":0,"complete_matches":0}
    path=here/f"checker_tests_{stamp}.json"
    with path.open("x") as f:json.dump(out,f,ensure_ascii=False,indent=2)
    print(path)
    raise SystemExit(not result.wasSuccessful())
