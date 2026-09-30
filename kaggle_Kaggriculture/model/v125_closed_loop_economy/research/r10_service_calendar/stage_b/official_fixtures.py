"""人工条件输入；导入不创建环境、不调用编译器或候选。"""
from copy import deepcopy

RULES_SHA = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
CROP_MAX_DAY = {"WHEAT": 4, "CARROT": 3, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 12}


def plant(crop, planted_day, **changes):
    ongoing = crop in ("TOMATO", "STRAWBERRY")
    t = {"kind": "PLANT", "crop": crop, "planted_day": planted_day,
         "watered_today": False, "consecutive_unwatered": 1,
         "yield_units": 0 if ongoing else 1,
         "max_lifespan_step": -1 if ongoing else (planted_day + CROP_MAX_DAY[crop] + 1) * 24,
         "fertilized_until_day": -1}
    t.update(changes)
    return t


def animal(item, placed_day, **changes):
    t = {"kind": "COOP" if item == "GOOSE" else "PASTURE", "animal": item,
         "placed_day": placed_day, "yield_units": 0, "consecutive_unfed": 0,
         "fed_today": False, "cared_today": False, "fertilizer_available": False,
         "pending_care_bonus": 0}
    t.update(changes)
    return t


def row(pos, tile):
    return {"pos": list(pos), "tile": tile}


def certificate_fixtures():
    """每项均完整枚举人工农场资产；日历从该条件日初编译。"""
    six = [row(p, plant("MELON", 12)) for p in ((3, 4), (3, 3), (3, 2), (3, 1), (2, 1), (1, 1))]
    cow = [row((3, 4), animal("COW", 0, yield_units=6, fertilizer_available=True, pending_care_bonus=2))]
    mixed = cow + [row((4, 3), animal("SHEEP", 0, yield_units=3, fertilizer_available=True)),
                   row((3, 3), animal("GOOSE", 0, yield_units=2, fertilizer_available=True)),
                   row((2, 4), plant("MELON", 0, yield_units=5)),
                   row((4, 2), plant("CARROT", 9, yield_units=3)),
                   row((2, 3), plant("TOMATO", 2, yield_units=2, consecutive_unwatered=0))]
    terminal = [row((3, 4), animal("COW", 0, yield_units=6, fertilizer_available=True)),
                row((4, 3), plant("MELON", 17, yield_units=5)),
                row((3, 3), plant("TOMATO", 20, yield_units=2, consecutive_unwatered=0))]
    cases = [
        {"id": "six_melon_water", "day": 12, "n_hands": 0, "tiles": six, "shed": {}, "reserve": {}, "buy": 0},
        {"id": "cow_all_services_two_products", "day": 12, "n_hands": 1, "tiles": cow, "shed": {}, "reserve": {"FERTILIZER": 12}, "buy": 1},
        {"id": "all_assets_mixed_twelve_hands", "day": 12, "n_hands": 12, "tiles": mixed,
         "shed": {"WHEAT": 1, "FERTILIZER": 12}, "reserve": {"WHEAT": 1, "FERTILIZER": 12}, "buy": 2},
        {"id": "warehouse_99_cow_delivery", "day": 12, "n_hands": 1, "tiles": cow,
         "shed": {"WHEAT": 1, "FERTILIZER": 12, "MELON": 86}, "reserve": {"WHEAT": 1, "FERTILIZER": 12}, "buy": 0},
        {"id": "twelve_hires_sixteen_wheat", "day": 12, "n_hands": 12, "tiles": [],
         "shed": {}, "reserve": {"WHEAT": 16}, "buy": 16},
        {"id": "terminal_day_mixed_delivery", "day": 29, "n_hands": 12, "tiles": terminal,
         "shed": {"FERTILIZER": 12}, "reserve": {"FERTILIZER": 12}, "buy": 0},
    ]
    for case in cases:
        case["provenance"] = {"kind": "artificial_condition", "natural_future_reachability": "NOT_TESTED",
                              "full_supplied_farm_asset_enumeration": True,
                              "cash": "100000 artificial funds; actual prices and commits remain official"}
    return deepcopy(cases)


def frame(farmer=("PASS",), hands=(), market=()):
    return {"farmer": list(farmer), "hands": [list(x) for x in hands], "market": [list(x) for x in market]}


def raw_fixtures():
    """短片段含刻意无效动作，不称为 FEASIBLE 证书；分别记录预期 no-op。"""
    defaults = {"day": 12, "hour": 0, "positions": [[4, 4]], "inventories": [{}], "shed": {}, "tiles": []}
    cases = [
        {"id": "hire_birth_after_actions", "frames": [frame(market=[["HIRE"]] * 9 + [["BUY_PRODUCT", "WHEAT", 16]]),
            frame(farmer=["NORTH"], hands=[["NORTH"]] * 9, market=[["HIRE"]] * 3), frame(hands=[["PASS"]] * 12)]},
        {"id": "prebirth_hand_cannot_act", "frames": [frame(hands=[["NORTH"]], market=[["HIRE"]]), frame(hands=[["NORTH"]])]},
        {"id": "eleventh_market_order_ignored", "frames": [frame(market=[["HIRE"]] * 10 + [["BUY_PRODUCT", "WHEAT", 1]])]},
        {"id": "buy_available_next_hour", "frames": [frame(["PICKUP", "WHEAT", 4], market=[["BUY_PRODUCT", "WHEAT", 4]]), frame(["PICKUP", "WHEAT", 4])]},
        {"id": "shared_one_wheat_two_feeds", "positions": [[4, 4], [5, 4]], "inventories": [{}, {}], "shed": {"WHEAT": 1},
         "tiles": [row((4, 3), animal("COW", 0)), row((5, 3), animal("SHEEP", 0))],
         "frames": [frame(["PICKUP", "WHEAT", 4], [["PICKUP", "WHEAT", 4]]),
                    frame(["NORTH"], [["NORTH"]]), frame(["FEED"], [["FEED"]]), frame(["FEED"], [["FEED"]])]},
        {"id": "same_animal_feed_twice", "positions": [[4, 3]], "inventories": [{"WHEAT": 2}], "tiles": [row((4, 3), animal("COW", 0))],
         "frames": [frame(["FEED"]), frame(["FEED"])]},
        {"id": "place_one_product_at_a_time", "inventories": [{"MILK": 2, "FERTILIZER": 1}],
         "frames": [frame(["PLACE", "MILK", 2]), frame(["PLACE", "FERTILIZER", 1])]},
        {"id": "shared_warehouse_capacity", "positions": [[4, 4], [5, 4]], "inventories": [{"MILK": 2}, {"WOOL": 2}],
         "shed": {"WHEAT": 99}, "frames": [frame(["PLACE", "MILK", 2], [["PLACE", "WOOL", 2]])]},
        {"id": "later_sell_cannot_preclear_place", "inventories": [{"MILK": 2}], "shed": {"WHEAT": 99},
         "frames": [frame(["PLACE", "MILK", 2], market=[["SELL", "WHEAT", 2]])]},
        {"id": "pickup_frees_space_before_buy", "shed": {"WHEAT": 100},
         "frames": [frame(["PICKUP", "WHEAT", 4], market=[["BUY_PRODUCT", "WHEAT", 4]])]},
        {"id": "terminal_h22_place_sell", "day": 29, "hour": 22, "inventories": [{"MILK": 2}],
         "frames": [frame(["PLACE", "MILK", 2], market=[["SELL", "MILK", 2]])]},
        {"id": "terminal_h22_remote_harvest", "day": 29, "hour": 22, "positions": [[3, 4]],
         "tiles": [row((3, 4), animal("COW", 0, yield_units=2))], "frames": [frame(["HARVEST"], market=[["SELL", "MILK", 2]])]},
        {"id": "fed_care_prior_bonus_eod", "day": 7, "hour": 22, "positions": [[3, 4]], "inventories": [{"WHEAT": 1}],
         "tiles": [row((3, 4), animal("COW", 0, pending_care_bonus=2))], "frames": [frame(["FEED"]), frame(["CARE"])]},
        {"id": "unfed_care_no_bonus_eod", "day": 7, "hour": 23, "positions": [[3, 4]],
         "tiles": [row((3, 4), animal("COW", 0, pending_care_bonus=2))], "frames": [frame(["CARE"])]},
        {"id": "ongoing_fourth_production_lifespan", "day": 10, "hour": 23, "positions": [[3, 4]],
         "tiles": [row((3, 4), plant("TOMATO", 0, yield_units=3, fertilized_until_day=10))], "frames": [frame(["WATER"])]},
        {"id": "one_shot_harvest_destroys_asset", "day": 12, "positions": [[3, 4]],
         "tiles": [row((3, 4), plant("MELON", 0, yield_units=6))], "frames": [frame(["HARVEST"]), frame(["WATER"]), frame(["HARVEST"])]},
        {"id": "missed_care_kills_at_eod", "day": 12, "hour": 23,
         "tiles": [row((3, 4), plant("MELON", 12)), row((4, 3), animal("COW", 0, consecutive_unfed=1))], "frames": [frame()]},
        {"id": "eod_partial_drop_is_not_place", "day": 12, "hour": 23, "positions": [[3, 4], [2, 4]],
         "inventories": [{"MILK": 2, "FERTILIZER": 1}, {"WOOL": 2}], "shed": {"WHEAT": 99}, "frames": [frame(hands=[["PASS"]])]},
        {"id": "lifespan_last_frame_harvest_allowed", "day": 12, "positions": [[3, 4]],
         "tiles": [row((3, 4), plant("MELON", 0, yield_units=1, max_lifespan_step=288))], "frames": [frame(["HARVEST"])]},
        {"id": "lifespan_move_too_late", "day": 12,
         "tiles": [row((3, 4), plant("MELON", 0, yield_units=1, max_lifespan_step=288))], "frames": [frame(["WEST"]), frame(["HARVEST"])]},
    ]
    return [deepcopy(defaults | c) for c in cases]
