#!/usr/bin/env python3
"""Build a self-contained experimental P0-A Kaggle archive."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
PARENT = ROOT / "kaggle_Kaggriculture" / "model" / "v16_gold_strategy_research" / "top_complete_portfolio" / "main.py"
EXPECTED_PARENT_SHA256 = "b52e62545fb6bdc93f9e947f9a829e348dd6119ee9daf7d8eba7df9aec29a4b1"


OVERLAY = r'''

# --- V18 P0-A experimental market-only one-step MPC overlay ---
_V18_PARENT_AGENT = agent
_V18_SAFE_PRODUCTS = {"CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"}
_V18_SHOP_PRODUCTS = {
    "BAKERY": {"WHEAT": 1, "EGG": 1},
    "BRUNCH_SPOT": {"WHEAT": 1, "EGG": 1, "STRAWBERRY": 1},
    "FARMERS_MARKET": {"WHEAT": 1, "CARROT": 1, "TOMATO": 1, "STRAWBERRY": 1},
    "ICE_CREAM_SHOP": {"WHEAT": 1, "STRAWBERRY": 1, "MILK": 1},
    "PET_CAFE": {"CARROT": 2},
    "PIZZA_SHOP": {"WHEAT": 1, "TOMATO": 1, "MILK": 1},
    "SMOOTHIE_SHOP": {"STRAWBERRY": 1, "MILK": 1},
    "YARN_STORE": {"WOOL": 2},
}
_V18_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_V18_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_V18_LAND_COST = (1000, 2000, 4000)
_V18_LEAD_CEILING = 5000
_V18_QUANTITY_CAP = 5
_V18_SHED_CEILING = 80
_V18_CASH_FLOOR = 3000
_V18_MIN_STEP = 72
_V18_MAX_STEP = 708
_V18_STATE = {
    0: {"last": -1, "due_step": -1, "due": {}},
    1: {"last": -1, "due_step": -1, "due": {}},
}


def _v18_step(obs):
    if obs.get("step") is not None:
        return int(obs.get("step") or 0)
    return int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)


def _v18_seat(obs):
    return 1 if int(obs.get("player", 0) or 0) == 1 else 0


def _v18_fib(index):
    a, b = 0, 1
    for _ in range(max(0, index)):
        a, b = b, a + b
    return a


def _v18_fixed_spend_upper_bound(obs, action):
    farm = obs["farms"][_v18_seat(obs)]
    hires = int(farm.get("hires_today", 0) or 0)
    quadrants = len(farm.get("unlocked_quadrants", []) or [])
    spend = 0
    product_bought = {}
    market_inventory = dict((obs.get("market") or {}).get("inventory") or {})
    for order in action.get("market") or []:
        if not order:
            continue
        op = str(order[0])
        if op == "BUY_PRODUCT":
            if len(order) < 3:
                return None
            item = str(order[1])
            quantity = max(0, int(order[2] or 0))
            already = product_bought.get(item, 0)
            start = int(market_inventory.get(item, 0) or 0) - 100 - already
            for offset in range(quantity):
                spend += int(_market_price(item, start - offset - 1))
            product_bought[item] = already + quantity
        if op == "HIRE":
            spend += _v18_fib(hires)
            hires += 1
        elif op == "BUY_LAND":
            extra = quadrants - 1
            if not 0 <= extra < len(_V18_LAND_COST):
                return None
            spend += _V18_LAND_COST[extra]
            quadrants += 1
        elif op == "BUY_SEED" and len(order) >= 3:
            if str(order[1]) not in _V18_SEED_COST:
                return None
            spend += _V18_SEED_COST[str(order[1])] * max(0, int(order[2] or 0))
        elif op == "BUY_ANIMAL" and len(order) >= 3:
            if str(order[1]) not in _V18_ANIMAL_COST:
                return None
            spend += _V18_ANIMAL_COST[str(order[1])] * max(0, int(order[2] or 0))
    return spend


def _v18_town_drain(obs, item, step):
    if step % 4 != 0:
        return 0
    drain = 1 if step % 24 == 0 and item != "FERTILIZER" else 0
    for shop in list((obs.get("town") or {}).get("unlocked_shops") or []):
        drain += _V18_SHOP_PRODUCTS.get(str(shop), {}).get(item, 0)
    return drain


def _v18_pickup_reserve(action, item):
    reserve = 0
    for order in [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]:
        if order and order[0] == "PICKUP" and len(order) >= 2 and str(order[1]) == item:
            reserve += max(1, int(order[2] or 1)) if len(order) >= 3 else 1
    return reserve


def _v18_has_shed_unit_action(action):
    return any(
        order and str(order[0]) in {"PICKUP", "DROP", "PLACE"}
        for order in [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    )


def _v18_merge_front(market, due):
    remaining = {item: max(0, int(qty)) for item, qty in due.items() if int(qty) > 0}
    out = []
    for item in sorted(remaining):
        quantity = remaining[item]
        for order in market:
            if order and order[0] == "SELL" and len(order) >= 3 and str(order[1]) == item:
                quantity += max(0, int(order[2] or 0))
                order[2] = 0
        out.append(["SELL", item, quantity])
    out.extend(
        order for order in market
        if not (order and order[0] == "SELL" and len(order) >= 3 and int(order[2] or 0) <= 0)
    )
    return out[:10]


def _v18_market_overlay(obs, configuration=None):
    action = _V18_PARENT_AGENT(obs, configuration)
    action = copy.deepcopy(action)
    action["market"] = [list(order) for order in (action.get("market") or [])][:10]
    seat = _v18_seat(obs)
    step = _v18_step(obs)
    local = _V18_STATE[seat]
    if step == 0 or step < int(local["last"]):
        local.update(last=step, due_step=-1, due={})
    local["last"] = step

    if int(local["due_step"]) == step:
        shed = dict((obs.get("private") or {}).get("shed") or {})
        executable = {}
        for item, quantity in dict(local["due"]).items():
            available = max(0, int(shed.get(item, 0) or 0) - _v18_pickup_reserve(action, item))
            sold = min(max(0, int(quantity)), available)
            if sold > 0:
                executable[item] = sold
        if executable:
            action["market"] = _v18_merge_front(action["market"], executable)
        local.update(due_step=-1, due={})

    farms = list(obs.get("farms") or [{}, {}])
    own = farms[seat] if len(farms) > seat else {}
    rival = farms[1 - seat] if len(farms) > 1 else {}
    money_lead = int(own.get("money", 0) or 0) - int(rival.get("money", 0) or 0)
    spend = _v18_fixed_spend_upper_bound(obs, action)
    shed = dict((obs.get("private") or {}).get("shed") or {})
    shed_total = sum(max(0, int(value or 0)) for value in shed.values())
    can_plan = (
        int(local["due_step"]) < 0
        and _V18_MIN_STEP <= step <= _V18_MAX_STEP
        and money_lead <= _V18_LEAD_CEILING
        and spend is not None
        and int(own.get("money", 0) or 0) >= int(spend) + _V18_CASH_FLOOR
        and shed_total <= _V18_SHED_CEILING
        and len(action["market"]) < 10
        and not _v18_has_shed_unit_action(action)
        and step + 1 < len(_ACTIONS)
        and not _v18_has_shed_unit_action(_ACTIONS[step + 1] or {})
    )
    if can_plan:
        due = {}
        kept = []
        remaining = {item: max(0, int(value or 0)) for item, value in shed.items()}
        for order in action["market"]:
            if not (order and order[0] == "SELL" and len(order) >= 3 and str(order[1]) in _V18_SAFE_PRODUCTS):
                kept.append(order)
                continue
            item = str(order[1])
            quantity = max(0, int(order[2] or 0))
            executable = min(quantity, remaining.get(item, 0))
            remaining[item] = max(0, remaining.get(item, 0) - executable)
            move = min(executable, _V18_QUANTITY_CAP) if _v18_town_drain(obs, item, step) > 0 else 0
            if move > 0:
                due[item] = due.get(item, 0) + move
            if quantity - move > 0:
                kept.append(["SELL", item, quantity - move])
        if due:
            action["market"] = kept[:10]
            local.update(due_step=step + 1, due=due)
    return action


del agent
def agent(obs, configuration=None):
    return _v18_market_overlay(obs, configuration)
'''


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parent = PARENT.read_bytes()
    if sha256(parent) != EXPECTED_PARENT_SHA256:
        raise RuntimeError("frozen V17 parent hash mismatch")
    main_bytes = parent.rstrip() + b"\n" + OVERLAY.encode("utf-8")
    (HERE / "main.py").write_bytes(main_bytes)

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        info = tarfile.TarInfo("main.py")
        info.size = len(main_bytes)
        info.mode = 0o644
        info.mtime = 0
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        tar.addfile(info, io.BytesIO(main_bytes))
    archive_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=archive_buffer, mode="wb", filename="", mtime=0) as gz:
        gz.write(tar_buffer.getvalue())
    archive = archive_buffer.getvalue()
    (HERE / "submission.tar.gz").write_bytes(archive)

    manifest = {
        "status": "EXPERIMENTAL_P0_A_REQUESTED_FOR_SUBMISSION_DESPITE_FAILED_RESEARCH_GATE",
        "parent_main_sha256": EXPECTED_PARENT_SHA256,
        "main_sha256": sha256(main_bytes),
        "archive_sha256": sha256(archive),
        "main_bytes": len(main_bytes),
        "archive_bytes": len(archive),
        "archive_members": ["main.py"],
        "self_contained": True,
        "local_file_imports": False,
        "overlay": {
            "market_only": True,
            "lead_ceiling": 5000,
            "quantity_cap": 5,
            "shed_ceiling": 80,
            "cash_floor": 3000,
            "step_range": [72, 708]
        },
        "development_evidence": {
            "source_date": "2026-08-25",
            "seed_range": [50008, 50027],
            "games": 240,
            "score_uplift_pp": 0.0,
            "research_gate_passed": False,
            "decision": "PACKAGED_ONLY_BECAUSE_USER_EXPLICITLY_REQUESTED_BOTH_P0_SUBMISSIONS"
        },
        "remote_submitted": False
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

