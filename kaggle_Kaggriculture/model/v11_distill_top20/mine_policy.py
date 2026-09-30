"""策略结构挖掘：每队的关键决策以哪些公开信号为条件。
输出 lib/policy_cards.json 与可读摘要。"""
import gzip, json, pathlib, collections, statistics, hashlib
HERE = pathlib.Path(__file__).resolve().parent
LIB = HERE / "lib"
SHOPS = {"BAKERY": ["EGG","WHEAT"], "PIZZA_SHOP": ["MILK","TOMATO","WHEAT"], "BRUNCH_SPOT": ["EGG","WHEAT","STRAWBERRY"],
         "YARN_STORE": ["WOOL"], "ICE_CREAM_SHOP": ["STRAWBERRY","MILK","WHEAT"], "PET_CAFE": ["CARROT"],
         "SMOOTHIE_SHOP": ["STRAWBERRY","MILK"], "FARMERS_MARKET": ["WHEAT","CARROT","TOMATO","STRAWBERRY"]}
DAIRY = {"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}; BERRY = {"BRUNCH_SPOT","ICE_CREAM_SHOP","SMOOTHIE_SHOP","FARMERS_MARKET"}

def fullhash(acts): return hashlib.sha1("|".join(json.dumps(a, sort_keys=True) for a in acts[:719]).encode()).hexdigest()[:8]
def h(acts, n): return hashlib.sha1("|".join(json.dumps(a, sort_keys=True) for a in acts[:n]).encode()).hexdigest()[:8]

def features(g):
    shops = g["shops"]
    yarn_days = sorted(t // 24 for s, t in shops if s == "YARN_STORE")
    f = {"first_yarn": yarn_days[0] if yarn_days else None, "n_yarn": len(yarn_days),
         "n_dairy_by_d8": sum(1 for s, t in shops if s in DAIRY and t <= 192),
         "n_berry_by_d8": sum(1 for s, t in shops if s in BERRY and t <= 192),
         "n_dairy": sum(1 for s, t in shops if s in DAIRY), "n_berry": sum(1 for s, t in shops if s in BERRY)}
    buys = collections.Counter(); buy_day = collections.defaultdict(list); land = []; sells = collections.Counter(); hires = 0
    for t, a in enumerate(g["actions"]):
        for m in a.get("market") or []:
            if m[0] == "BUY_ANIMAL": buys[m[1]] += int(m[2]); buy_day[m[1]].extend([t // 24] * int(m[2]))
            elif m[0] == "BUY_SEED": buys["seed:" + m[1]] += int(m[2])
            elif m[0] == "BUY_LAND": land.append(t // 24)
            elif m[0] == "SELL": sells[m[1]] += int(m[2])
            elif m[0] == "HIRE": hires += 1
    f.update({"sheep": buys["SHEEP"], "cow": buys["COW"], "goose": buys["GOOSE"],
              "sheep_after_d8": sum(1 for d in buy_day["SHEEP"] if d >= 8),
              "straw_seed": buys["seed:STRAWBERRY"], "melon_seed": buys["seed:MELON"], "land_days": land, "hires": hires,
              "sell_wool": sells["WOOL"], "sell_milk": sells["MILK"], "sell_straw": sells["STRAWBERRY"], "sell_melon": sells["MELON"],
              "bank": g["r_me"] or 0, "won": int((g["r_me"] or 0) > (g["r_opp"] or 0))})
    return f

def corr(xs, ys):
    n = len(xs)
    if n < 6: return None
    mx, my = sum(xs)/n, sum(ys)/n
    sx = (sum((x-mx)**2 for x in xs)/n) ** .5; sy = (sum((y-my)**2 for y in ys)/n) ** .5
    if sx == 0 or sy == 0: return 0.0
    return sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / n / sx / sy

cards = {}
for fn in sorted(LIB.glob("*.json.gz")):
    team = fn.stem.replace(".json", "")
    games = json.load(gzip.open(fn, "rt"))["games"]
    if len(games) < 20: continue
    F = [features(g) for g in games]
    uniq = len({fullhash(g["actions"]) for g in games})
    d3 = len({h(g["actions"], 72) for g in games}); d6 = len({h(g["actions"], 144) for g in games}); d10 = len({h(g["actions"], 240) for g in games})
    def grp(key):
        out = {}
        for label, sel in [("yarn=none", [f for f in F if f["first_yarn"] is None]),
                           ("yarn<=5", [f for f in F if f["first_yarn"] is not None and f["first_yarn"] <= 5]),
                           ("yarn8-14", [f for f in F if f["first_yarn"] is not None and 8 <= f["first_yarn"] <= 14]),
                           ("yarn>=17", [f for f in F if f["first_yarn"] is not None and f["first_yarn"] >= 17])]:
            if len(sel) >= 5: out[label] = round(statistics.median(f[key] for f in sel), 1)
        return out
    card = {"games": len(games), "uniq_tapes": uniq, "prefix_clusters_d3_d6_d10": [d3, d6, d10],
            "winrate": round(sum(f["won"] for f in F) / len(F), 3), "bank_med": statistics.median(f["bank"] for f in F),
            "sheep_by_yarn": grp("sheep"), "sheep_after_d8_by_yarn": grp("sheep_after_d8"),
            "cow_by_yarn": grp("cow"), "straw_seed_by_yarn": grp("straw_seed"), "bank_by_yarn": grp("bank"),
            "corr_cow_vs_dairy_shops": corr([f["n_dairy"] for f in F], [f["cow"] for f in F]),
            "corr_straw_vs_berry_shops": corr([f["n_berry"] for f in F], [f["straw_seed"] for f in F]),
            "corr_sheep_vs_nyarn": corr([f["n_yarn"] for f in F], [f["sheep"] for f in F]),
            "land_days_mode": collections.Counter(tuple(f["land_days"]) for f in F).most_common(2),
            "hires_med": statistics.median(f["hires"] for f in F)}
    cards[team] = card
json.dump(cards, open(LIB / "policy_cards.json", "w"), ensure_ascii=False, indent=1)
print(f"{'team':<20}{'n':>5}{'uniq':>6}{'d3/d6/d10':>12}{'wr':>6}{'bank':>8}  sheep(by yarn none/<=5/8-14/>=17)   r(sheep,nyarn) r(cow,dairy) r(straw,berry)")
for team, c in sorted(cards.items(), key=lambda kv: -kv[1]["winrate"]):
    s = c["sheep_by_yarn"]; sb = "/".join(str(s.get(k, "-")) for k in ("yarn=none", "yarn<=5", "yarn8-14", "yarn>=17"))
    r = lambda v: f"{v:+.2f}" if isinstance(v, float) else "  -  "
    print(f"{team:<20}{c['games']:>5}{c['uniq_tapes']:>6}{str(c['prefix_clusters_d3_d6_d10']):>12}{c['winrate']:>6.2f}{c['bank_med']:>8.0f}  {sb:<28} {r(c['corr_sheep_vs_nyarn']):>8} {r(c['corr_cow_vs_dairy_shops']):>10} {r(c['corr_straw_vs_berry_shops']):>10}")
print("MINE_DONE")
