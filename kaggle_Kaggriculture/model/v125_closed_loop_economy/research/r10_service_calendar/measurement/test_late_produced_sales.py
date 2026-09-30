"""纯人工数据反例；不读真实对局、不重放、不调用完整候选。"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
MODEL = next(p for p in HERE.parents if p.name == "v125_closed_loop_economy")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def event(step, kind, item=None, quantity=None, seat=0, **kw):
    result = {"decision_step": step, "recorded_step": step + 1, "day": step // 24, "hour": step % 24, "kind": kind, "seat": seat}
    if item is not None: result["item"] = item
    if quantity is not None: result["quantity"] = quantity
    result.update(kw)
    return result


def sale(step, price, item="MILK", qty=1, seat=0):
    return event(step, "market", item, qty, seat, op="SELL", price=price, shed_item_before=qty, shed_item_after=0)


def own_for(events, products, seat=0, initial=None):
    bal = {item: {"initial": (initial or {}).get(item, 0), "harvested": 0, "buy_product": 0, "sell": 0,
                  "fertilize": 0, "eod_overflow": 0, "manual_drop_overflow": 0, "terminal_inventory": 0, "residual": 0} for item in products}
    for e in events:
        if e["seat"] != seat: continue
        item, kind = e.get("item"), e["kind"]
        if item in bal:
            if kind == "harvest": bal[item]["harvested"] += e["quantity"]
            if kind == "market" and e["op"] == "BUY_PRODUCT": bal[item]["buy_product"] += e["quantity"]
            if kind == "market" and e["op"] == "SELL": bal[item]["sell"] += e["quantity"]
            if kind == "fertilize": bal[item]["fertilize"] += e["quantity"]
        if kind in ("eod_inventory_drop", "manual_drop_overflow"):
            for p, n in e["discarded" if kind == "eod_inventory_drop" else "quantity"].items():
                if p in bal: bal[p]["eod_overflow" if kind == "eod_inventory_drop" else "manual_drop_overflow"] += n
    for row in bal.values():
        row["terminal_inventory"] = row["initial"] + row["harvested"] + row["buy_product"] - row["sell"] - row["fertilize"] - row["eod_overflow"] - row["manual_drop_overflow"]
    return {"inventory_balance": bal, "all_inventory_residual_zero": True}


def main():
    tool = HERE / "assess_late_produced_sales.py"
    first = MODEL / "research/r8_terminal_net_selection/summarize_first_produced_sale_v3.py"
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    sources = {str(p): sha(p) for p in (tool, first, Path(__file__).resolve())}
    m = load(tool, "r10_measurement_under_test"); origin = load(first, "frozen_first_sale_for_r10_pure_tests")
    assert sha(first) == m.SHA["first_sale"]
    checks = []

    def check(name, ok, evidence=None):
        checks.append({"name": name, "passed": bool(ok), "evidence": evidence})

    def calc(events, own=None, seat=0):
        return m.window_sales(own or own_for(events, m.PRODUCTS, seat), events, seat, origin)

    events = [event(200, "harvest", "MILK", 3), sale(263, 7), sale(264, 11), sale(718, 13)]
    value = calc(events)
    check("263_excluded_264_and_718_included", value["cash"] == 24 and value["units"] == 2 and [e["decision_step"] for e in value["sale_receipts"]] == [264, 718], value)
    check("recorded_719_maps_to_decision718", value["sale_receipts"][-1]["recorded_step"] == 719)
    invalid = deepcopy(events); invalid[-1] = sale(719, 13)
    value = calc(invalid)
    check("decision719_rejected_not_silently_excluded", value["status"] == "PENDING_PROVENANCE" and value["cash"] is None, value["issues"])
    check("complete_zero_window_sales_is_real_zero", calc([event(200, "harvest", "MILK", 1), sale(263, 5)])["cash"] == 0)
    value = calc([])
    check("fully_zero_game_is_numeric_zero", value["status"] == "NUMERIC_COMPLETE" and value["cash"] == value["units"] == 0 and value["no_qualifying_sale"] is True)
    mixed = events[:3] + [sale(265, 999, qty=100, seat=1)] + events[3:]
    check("otherseat_sale_not_counted", calc(mixed)["cash"] == 24)
    fert = [event(264, "harvest", "FERTILIZER", 2), sale(265, 99, "FERTILIZER", 2)]
    value = calc(fert)
    check("fertilizer_included", value["cash"] == 198 and value["by_item"] == {"FERTILIZER": {"cash": 198, "units": 2}})
    wheat = [event(264, "harvest", "WHEAT", 3), sale(265, 50, "WHEAT", 3)]
    check("wheat_excluded", calc(wheat)["cash"] == 0)
    buymilk = [event(2, "market", "MILK", 1, op="BUY_PRODUCT", price=10), sale(264, 11)]
    value = calc(buymilk)
    check("external_buy_resale_pending_even_before_window", value["status"] == "PENDING_PROVENANCE" and value["cash"] is None, value["issues"])
    initial = own_for([sale(264, 11)], m.PRODUCTS, initial={"MILK": 1})
    check("initial_mixed_stock_pending", calc([sale(264, 11)], initial)["status"] == "PENDING_PROVENANCE")
    validmilk = [event(1, "harvest", "MILK", 1), sale(264, 11)]
    mixedfert = own_for(validmilk, m.PRODUCTS, initial={"FERTILIZER": 1})
    check("other_nonwheat_initial_stock_makes_whole_game_pending", calc(validmilk, mixedfert)["status"] == "PENDING_PROVENANCE")
    buywheat = [event(2, "market", "WHEAT", 1, op="BUY_PRODUCT", price=10)] + validmilk
    buywheat.sort(key=lambda e: e["decision_step"])
    check("outside_wheat_purchase_does_not_contaminate_nonwheat_origin", calc(buywheat)["cash"] == 11)
    outoforder = [sale(264, 11), event(265, "harvest", "MILK", 1)]
    check("sale_before_production_rejected", calc(outoforder)["status"] == "PENDING_PROVENANCE")
    loss = [event(264, "harvest", "FERTILIZER", 2), event(264, "fertilize", "FERTILIZER", 1),
            event(265, "eod_inventory_drop", discarded={"FERTILIZER": 1}), sale(266, 10, "FERTILIZER", 1)]
    check("consumed_or_lost_goods_cannot_be_sold_again", calc(loss)["status"] == "PENDING_PROVENANCE")
    valid_loss = loss[:-1]
    check("legal_consumption_and_loss_can_close_zero_sales", calc(valid_loss)["cash"] == 0)
    dup = deepcopy(validmilk); dup.append(deepcopy(dup[-1]))
    check("duplicate_sale_event_without_source_balance_fails", calc(dup, own_for(validmilk, m.PRODUCTS))["status"] == "PENDING_PROVENANCE")
    for label, field, bad in (("bool_seat", "seat", True), ("missing_recorded", "recorded_step", None),
                              ("bool_clock", "decision_step", True), ("wrong_day", "day", 9),
                              ("float_official_price", "price", 11.0), ("nan_price", "price", float("nan")),
                              ("bool_quantity", "quantity", True)):
        e = deepcopy(validmilk); e[-1][field] = bad
        value = calc(e, own_for(validmilk, m.PRODUCTS))
        check(label + "_pending", value["status"] == "PENDING_PROVENANCE" and value["cash"] is None)

    def rows(parent=100, child=120):
        return [{"candidate_id": v, "opponent": o, "seed": s, "seat": t, "source_key": str((v, o, s, t)),
                 "window": {"status": "NUMERIC_COMPLETE", "window_decisions": [264, 718], "cash": parent if v == "V125-R9" else child, "units": 1}} for v, o, s, t in sorted(m.EXPECTED)]
    check("exact20_percent_boundary_passes", m.assess(rows())["primary_mechanism_numeric_threshold_pass"])
    check("below20_percent_fails", not m.assess(rows(child=119))["primary_mechanism_numeric_threshold_pass"])
    zero = m.assess(rows(parent=0, child=0))
    check("parent_zero_pending_not_false_success", zero["data_integrity_pass"] and all(g["status"] == "PENDING" and g["at_least_20_percent"] is None for g in zero["groups"]))
    r = rows(); r.pop()
    check("missing_game_fails_closed", not m.assess(r)["data_integrity_pass"])
    r = rows(); r.append(deepcopy(r[0]))
    check("duplicate_cell_fails_closed", not m.assess(r)["data_integrity_pass"])
    r = rows(); r[0]["source_key"] = r[1]["source_key"]
    check("duplicate_source_key_fails_closed", not m.assess(r)["data_integrity_pass"])
    r = rows(); r[0]["window"]["status"] = "PENDING_PROVENANCE"
    check("one_pending_source_blocks_primary", not m.assess(r)["data_integrity_pass"])
    r = rows(); r[0]["window"]["window_decisions"] = [0, 239]
    check("early_window_cannot_substitute_late_window", not m.assess(r)["data_integrity_pass"])
    r = rows()
    for row in r:
        if row["candidate_id"] == "V125-R10": row["window"]["cash"] = 90 if row["seat"] == 0 else 150
    assessed = m.assess(r)
    check("seat_decline_cannot_be_hidden_by_pool", assessed["groups"][0]["at_least_20_percent"] and not assessed["primary_mechanism_numeric_threshold_pass"])
    r = rows()
    for row in r:
        row["window"]["cash"] = ([1, 1, 100] if row["candidate_id"] == "V125-R9" else [0, 0, 123])[m.SEEDS.index(row["seed"])]
    check("pooled_cash_not_mean_of_per_game_ratios", m.assess(r)["primary_mechanism_numeric_threshold_pass"])
    r = rows()
    for row in r:
        if row["seed"] == m.SEEDS[0]: row["window"]["cash"] = 0
    check("zero_sale_games_remain_in_complete24", m.assess(r)["observed_rows"] == 24 and m.assess(r)["primary_mechanism_numeric_threshold_pass"])
    for bad in (True, -1, None, 120.0):
        r = rows(); r[0]["window"]["cash"] = bad
        check("invalid_cash_" + repr(bad), not m.assess(r)["data_integrity_pass"])
    with tempfile.TemporaryDirectory(dir=HERE) as temp:
        p = Path(temp) / "toy.json"; p.write_text('{"value":1}')
        store = m.Inputs(); store.read(p); p.write_text('{"value":2}')
        try: store.verify(); drift = False
        except ValueError: drift = True
        check("parsed_source_drift_caught_before_output", drift)
        try: store.read(p); cross = False
        except ValueError: cross = True
        check("same_path_new_bytes_cannot_overwrite_fingerprint", cross)
        p.unlink()
        try: m.Inputs().read(p); missing = False
        except FileNotFoundError: missing = True
        check("missing_source_file_cannot_fill_zero", missing)
    changed = [p for p, value in sources.items() if sha(Path(p)) != value]
    check("test_and_frozen_dependency_sources_unchanged", not changed)
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "role": "PURE_SYNTHETIC_DATA_VALIDATION_NOT_MATCH",
              "passed": sum(c["passed"] for c in checks), "total": len(checks), "checks": checks, "source_sha256": sources,
              "candidate_calls": 0, "engine_steps": 0, "real_game_files_read": 0, "new_complete_matches": 0,
              "status": "PASS" if all(c["passed"] for c in checks) else "ERROR", "tool_freeze_status": "AWAIT_FINAL_DEVELOPMENT_PROTOCOL"}
    p = HERE / ("validation_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(p), "passed": result["passed"], "total": result["total"], "failed": [c["name"] for c in checks if not c["passed"]]}, ensure_ascii=False))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
