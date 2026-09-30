"""带上下文的抽取：在 24/72/144/216 步记录对手公开签名（tiles 计数、金币、hands）与自身金币。"""
import json, sys, gzip, pathlib, collections
from concurrent.futures import ProcessPoolExecutor
M = pathlib.Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
HERE = pathlib.Path(__file__).resolve().parent
CTX_STEPS = [24, 72, 144, 216]

def sig(farm):
    c = collections.Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict): c[t.get("crop") or t.get("animal") or t.get("kind")] += 1
    return dict(sorted(c.items()))

def one(h):
    f = M / f"date={h['day']}" / "data" / f"{h['ep']}.json"
    try: d = json.load(f.open())
    except Exception: return None
    seat = h["seat"]; steps = d["steps"]
    # steps[i].action 是"产生 steps[i] 的动作"，即第 i-1 回合的动作；turn t 的动作在 steps[t+1]
    acts = []
    for t in range(len(steps)):
        a = (steps[t + 1][seat].get("action") if t + 1 < len(steps) else None) or {}
        acts.append({"farmer": a.get("farmer") or ["PASS"], "hands": a.get("hands") or [], "market": a.get("market") or []})
    shops, seen = [], []
    for i, st in enumerate(steps):
        cur = list(((st[0].get("observation") or {}).get("town") or {}).get("unlocked_shops") or [])
        if len(cur) > len(seen):
            shops.extend([s, i] for s in cur[len(seen):]); seen = cur
    ctx = {}
    for s in CTX_STEPS:
        if s < len(steps):
            ob = steps[s][seat]["observation"]; me, opp = ob["farms"][seat], ob["farms"][1 - seat]
            ctx[str(s)] = {"opp_sig": sig(opp), "opp_money": round(opp["money"]), "opp_hands": len(opp.get("hands") or []),
                           "my_money": round(me["money"]), "wheat_px": ob["market"]["prices"]["WHEAT"]}
    return {"ep": h["ep"], "day": h["day"], "seat": seat, "seed": d["info"].get("seed"), "r_me": h["r_me"], "r_opp": h["r_opp"],
            "opp": h["opp"], "shops": shops, "ctx": ctx, "actions": acts}

def main():
    hits = json.load(open(HERE / "lib" / "hits.json"))
    for team in sys.argv[1:]:
        games = hits.get(team, [])
        with ProcessPoolExecutor(max_workers=6) as ex:
            out = [g for g in ex.map(one, games) if g]
        fn = HERE / "lib" / f"{team.replace(' ', '_')}_ctx.json.gz"
        with gzip.open(fn, "wt") as fh: json.dump({"team": team, "games": out}, fh)
        print(f"{team}: {len(out)} games -> {fn.name}", flush=True)

if __name__ == "__main__":
    main()
