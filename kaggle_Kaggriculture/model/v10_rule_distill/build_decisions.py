"""把 replay 库转成决策样本表：观测（商店揭示）→ 决策（购买/种植/雇佣/卖出时序）。
train = day <= 2026-08-30；holdout = 2026-08-31（M6 场景来源日，严禁用于挖规则）。"""
import gzip, json, pathlib, collections
HERE = pathlib.Path(__file__).resolve().parent
LIB = HERE.parent / "v5_tape_tree_hmoe" / "lib"
SHOPS = {"BAKERY": ["EGG","WHEAT"], "PIZZA_SHOP": ["MILK","TOMATO","WHEAT"], "BRUNCH_SPOT": ["EGG","WHEAT","STRAWBERRY"],
         "YARN_STORE": ["WOOL"], "ICE_CREAM_SHOP": ["STRAWBERRY","MILK","WHEAT"], "PET_CAFE": ["CARROT"],
         "SMOOTHIE_SHOP": ["STRAWBERRY","MILK"], "FARMERS_MARKET": ["WHEAT","CARROT","TOMATO","STRAWBERRY"]}
PRODS = ["WOOL","MILK","STRAWBERRY","MELON","CARROT","EGG","WHEAT","FERTILIZER"]

def features(shops):
    """只用商店揭示（可观测）。shops = [(name, step)]"""
    f = {}
    days = {s: [] for s in SHOPS}
    for name, step in shops:
        days.setdefault(name, []).append(step // 24)
    for s in SHOPS:
        f[f"n_{s}"] = len(days.get(s, []))
        f[f"first_{s}"] = min(days[s]) if days.get(s) else 99
    for p in ["WOOL","MILK","STRAWBERRY","EGG","CARROT"]:
        buyers = [s for s, items in SHOPS.items() if p in items]
        f[f"nshop_{p}"] = sum(f[f"n_{s}"] for s in buyers)
        f[f"nshop_{p}_by8"] = sum(1 for s in buyers for d in days.get(s, []) if d <= 8)
        f[f"nshop_{p}_by14"] = sum(1 for s in buyers for d in days.get(s, []) if d <= 14)
    return f

def decisions(acts):
    d = collections.Counter(); first_sell = {}; sell_tot = collections.Counter(); land = []; hires = 0
    for t, a in enumerate(acts):
        day = t // 24
        for m in a.get("market") or []:
            op = m[0]
            if op == "BUY_ANIMAL":
                d[f"{m[1]}_total"] += int(m[2])
                if day >= 8: d[f"{m[1]}_late"] += int(m[2])
                d[f"{m[1]}_d{min(day,29)//4*4}"] += int(m[2])
            elif op == "BUY_SEED":
                d[f"seed_{m[1]}"] += int(m[2])
            elif op == "BUY_LAND":
                land.append(day)
            elif op == "HIRE":
                hires += 1
            elif op == "SELL":
                sell_tot[m[1]] += int(m[2])
                first_sell.setdefault(m[1], day)
    out = dict(d); out["hires"] = hires
    out["land1"] = land[0] if land else 99; out["land2"] = land[1] if len(land) > 1 else 99; out["n_land"] = len(land)
    for p in PRODS:
        out[f"sell_{p}"] = sell_tot.get(p, 0); out[f"firstsell_{p}"] = first_sell.get(p, 99)
    return out

def main():
    rows = []
    for team in ["tetsuya","Crop_Dusta","Driz_Lo","yukino","MtN","OceanMix"]:
        for g in json.load(gzip.open(LIB / f"{team}.json.gz", "rt"))["games"]:
            r = {"team": team, "ep": str(g["ep"]), "date": g["day"], "seat": g["seat"], "won": int((g["r_me"] or 0) > (g["r_opp"] or 0)),
                 "bank": g["r_me"] or 0, "split": "holdout" if g["day"] >= "2026-08-31" else "train"}
            r.update(features(g["shops"])); r.update(decisions(g["actions"]))
            rows.append(r)
    json.dump(rows, open(HERE / "lib" / "decisions.json", "w"))
    c = collections.Counter((r["team"], r["split"]) for r in rows)
    print("样本数:", dict(c))

if __name__ == "__main__":
    main()
