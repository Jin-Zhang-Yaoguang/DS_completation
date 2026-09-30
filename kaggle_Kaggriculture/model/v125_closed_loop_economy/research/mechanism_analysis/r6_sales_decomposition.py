"""已核验 R0/R5/R6 诊断的量价会计拆解，不运行引擎或候选。"""
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import r5_feed_workload

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name):
    d = ROOT / name
    m = json.loads((d / "audit_manifest.json").read_text())
    val = json.loads((d / "validation.json").read_text())
    assert val["terminal_full_snapshot_matches_source"] and val["cash_rewards_match_source"] and val["all_item_inventory_conservation_zero_residual"]
    source = Path(m["source_games"]["path"])
    assert sha(source) == m["source_games"]["sha256"]
    j = json.loads(source.read_text().splitlines()[m["source_games"]["game_index"]])
    s = j["candidate_seat"]
    ledger = j["action_audit"]["actual_market_ledger"][s]
    analysis = json.loads((d / "analysis.json").read_text())["seats"][s]
    f = json.loads((d / "findings.json").read_text())["seats"][s]
    events = [json.loads(line) for line in gzip.open(d / "events.jsonl.gz", "rt")]
    sale_daily = {}
    for event in events:
        if event["seat"] == s and event["kind"] == "market" and event["op"] == "SELL":
            key = str(event["day"])
            item = event["item"]
            row = sale_daily.setdefault(key, {}).setdefault(item, {"quantity": 0, "cash": 0})
            row["quantity"] += event["quantity"]
            row["cash"] += event["price"]
    income = sum(ledger["SELL_cash"].values())
    costs = {k: sum(v.values()) for k, v in ledger.items() if k.endswith("_cash") and k != "SELL_cash"}
    assert 3000 + income - sum(costs.values()) == j["candidate_reward"]
    diagnostic = j["strategy_diagnostics"][s][str(s)]
    workload = r5_feed_workload.analyze(name)
    return {"directory": name, "source_trace_sha256": m["source_trace"]["sha256"],
            "source_games_sha256": sha(source), "candidate_sha256": m["candidate_entry_sha256"],
            "cash": j["candidate_reward"], "ledger": ledger, "cost_totals": costs, "revenue_total": income,
            "harvest": j["action_audit"]["harvest_qty"][s], "denominators": analysis["denominators"],
            "plantings_by_crop": dict(Counter(e["crop"] for e in events if e["kind"] == "plant" and e["seat"] == s)),
            "overflow": analysis["overflow"], "terminal_assets": analysis["terminal_assets"],
            "productive_drought_deaths": f["drought_loss_still_productive_count"],
            "unit_action_counts": f["unit_action_counts"],
            "workload": {k: v for k, v in workload.items() if k not in ("daily", "pickups", "overflow", "terminal_assets")},
            "experts_by_call": {k: v for k, v in diagnostic["metrics"].items() if k.startswith("expert_")},
            "daily_expert_crop_snapshots": [{k: row[k] for k in ("day", "expert", "crop_choice")} for row in diagnostic["daily"]],
            "daily_sales": sale_daily,
            "inputs": {name: sha(d / name) for name in ("audit_manifest.json", "validation.json", "analysis.json", "findings.json", "events.jsonl.gz")}}


def compare(left, right):
    ll, rr = left["ledger"], right["ledger"]
    products = sorted(set(ll["SELL_qty"]) | set(rr["SELL_qty"]))
    rows = []
    for product in products:
        q0, q1 = ll["SELL_qty"].get(product, 0), rr["SELL_qty"].get(product, 0)
        r0, r1 = ll["SELL_cash"].get(product, 0), rr["SELL_cash"].get(product, 0)
        p0, p1 = (Fraction(r0, q0) if q0 else None), (Fraction(r1, q1) if q1 else None)
        if q0 and q1:
            qty_effect = (q1 - q0) * (p0 + p1) / 2
            price_effect = (p1 - p0) * (q0 + q1) / 2
            exclusive_effect = 0
            assert qty_effect + price_effect == r1 - r0
        else:
            qty_effect, price_effect = None, None
            exclusive_effect = r1 - r0
        rows.append({"product": product, "harvest_left": left["harvest"].get(product, 0), "harvest_right": right["harvest"].get(product, 0),
                     "sold_left": q0, "sold_right": q1, "average_price_left": float(p0) if p0 is not None else None,
                     "average_price_right": float(p1) if p1 is not None else None, "revenue_left": r0, "revenue_right": r1,
                     "revenue_delta": r1 - r0, "quantity_accounting_effect": float(qty_effect) if qty_effect is not None else None,
                     "average_price_accounting_effect": float(price_effect) if price_effect is not None else None,
                     "one_sided_product_revenue_delta": exclusive_effect})
    no_wheat = [row for row in rows if row["product"] != "WHEAT"]
    non_wheat_revenue_delta = sum(row["revenue_delta"] for row in no_wheat)
    wheat_net = lambda ledger: ledger["SELL_cash"].get("WHEAT", 0) - ledger.get("BUY_PRODUCT_cash", {}).get("WHEAT", 0)
    non_wheat_cost = lambda value: sum(value["cost_totals"].values()) - value["ledger"].get("BUY_PRODUCT_cash", {}).get("WHEAT", 0)
    cash_bridge = {"non_wheat_sale_revenue_delta": non_wheat_revenue_delta,
                   "wheat_sale_minus_purchase_delta": wheat_net(rr) - wheat_net(ll),
                   "other_cost_delta": non_wheat_cost(right) - non_wheat_cost(left),
                   "cash_delta": right["cash"] - left["cash"]}
    assert cash_bridge["non_wheat_sale_revenue_delta"] + cash_bridge["wheat_sale_minus_purchase_delta"] - cash_bridge["other_cost_delta"] == cash_bridge["cash_delta"]
    return {"left": left["directory"], "right": right["directory"], "products": rows,
            "non_wheat_decomposition": {"quantity_accounting_effect": sum(row["quantity_accounting_effect"] or 0 for row in no_wheat),
                                        "average_price_accounting_effect": sum(row["average_price_accounting_effect"] or 0 for row in no_wheat),
                                        "one_sided_product_revenue_delta": sum(row["one_sided_product_revenue_delta"] for row in no_wheat)},
            "cash_bridge": cash_bridge}


def main():
    candidates = [load(name) for name in ("r0_pass_s0", "r5_pass_s0", "r6_pass_s0")]
    result = {"schema": "v125-opened-r6-sales-decomposition-v1", "script_sha256": sha(Path(__file__)),
              "workload_script_sha256": sha(ROOT / "r5_feed_workload.py"), "candidate_calls": 0, "engine_runs": 0,
              "definitions": {"average_price": "每商品真实SELL现金合计/真实SELL数量，不使用报价代替成交。",
                              "quantity_effect": "共同售出商品：(Q1-Q0)*(P0+P1)/2。",
                              "price_effect": "共同售出商品：(P1-P0)*(Q0+Q1)/2。两项为精确会计恒等式；并非控制其他变量的因果反事实。",
                              "one_sided_products": "仅一侧售出的商品单列收入差，不给未售出一侧臆造均价。",
                              "wheat": "小麦有反复买卖循环，净买卖额单列，不能把卖麦数量当全部自产。",
                              "price_boundary": "平均成交价格变化同时含不同商店需求、自产供给冲击、交易时点和品种/分派反馈；不能全部称外生商店效应。"},
              "candidates": candidates, "comparisons": [compare(candidates[1], candidates[2]), compare(candidates[0], candidates[2])]}
    (ROOT / "r6_sales_decomposition.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    for pair in result["comparisons"]:
        print(json.dumps(pair, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
