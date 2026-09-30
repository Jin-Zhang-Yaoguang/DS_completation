"""劳动力审计：单人局逐 verb 计数 + 田间状态（漏浇/死亡/肥效覆盖）。"""
import sys, json, collections
from fidelity import make_agent, engine
def run(spec, seed):
    a = make_agent(spec)
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    verbs = collections.Counter(); step = 0
    weed_created = 0; straw_fert_days = 0; straw_prod_days = 0; straw_dead = 0
    prev_straw = {}
    while not engine._val(g.done):
        o0 = g.observe(0)
        day = step // 24
        if step % 24 == 23:
            tiles = o0["farms"][0]["tiles"]
            for r, row in enumerate(tiles):
                for c, x in enumerate(row):
                    if isinstance(x, dict) and x.get("crop") == "STRAWBERRY":
                        age = day - x.get("planted_day", day)
                        if age >= 9:
                            straw_prod_days += 1
                            if x.get("fertilized_until_day", -1) >= day: straw_fert_days += 1
                        prev_straw[(r, c)] = day
                    elif isinstance(x, dict) and x.get("kind") == "WEED" and (r, c) in prev_straw and prev_straw[(r, c)] >= day - 1:
                        straw_dead += 1; prev_straw.pop((r, c))
        try: act = a(o0)
        except Exception: act = {"farmer": ["PASS"], "hands": [], "market": []}
        for x in [act.get("farmer") or []] + list(act.get("hands") or []):
            if x:
                v = str(x[0])
                verbs["MOVE" if v in ("NORTH","SOUTH","EAST","WEST") else v] += 1
        g.step(act, {"farmer": ["PASS"], "hands": [], "market": []})
        step += 1
    tot = sum(verbs.values())
    print(f"{spec.split('/')[-1][:24]:24s} bank={engine._val(g.reward(0)):.0f} total_acts={tot}")
    print("  ", {k: v for k, v in verbs.most_common(14)})
    print(f"   straw: prod_days={straw_prod_days} fert_covered={straw_fert_days} ({straw_fert_days/max(1,straw_prod_days):.0%}) died={straw_dead}")
if __name__ == "__main__":
    for spec in sys.argv[1].split(","):
        run(spec, int(sys.argv[2]))
