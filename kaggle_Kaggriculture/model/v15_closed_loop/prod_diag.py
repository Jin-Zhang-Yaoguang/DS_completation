"""产量归因：双方每天实际收获（按产品）、喂养/照料/浇水/施肥次数、动物数、植株数。"""
import sys, json, collections, os
H = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v4_demand_race/harness"
sys.path.insert(0, H); os.chdir(H)
from engine import fresh_agent, load_scenario
W = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture"
def val(x): return x() if callable(x) else x
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
sc = json.load(open("scenarios_64.json"))[idx]
c = fresh_agent(f"{W}/model/v15_closed_loop/main.py"); o = fresh_agent(f"{W}/model/v10_rule_distill/dist/main.py")
ags = [c, o]
k = load_scenario(); g = k.Game(seed=sc["seed"]); sched = sc["shops"]; g.force_shops([n for n, st in sched if st <= 0]); step = 0
prod = [collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)]
while not val(g.done):
    obs = [g.observe(0), g.observe(1)]; acts = [ags[i].agent(obs[i]) for i in range(2)]
    for i in range(2):
        f = obs[i]["farms"][i]; d = obs[i]["day"]; P = prod[i][d]
        pos = [tuple(f["farmer"])] + [tuple(x) for x in f["hands"]]; units = [acts[i].get("farmer") or ["PASS"]] + list(acts[i].get("hands") or [])
        for j, u in enumerate(units):
            if j >= len(pos) or not u: continue
            x, y = pos[j]; t = f["tiles"][y][x]
            if not isinstance(t, dict): continue
            if u[0] == "HARVEST" and t.get("yield_units", 0) > 0:
                item = t.get("crop") or {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}[t["animal"]]
                P["H_" + item] += t["yield_units"]
            elif u[0] == "FEED" and "animal" in t and not t.get("fed_today"): P["feed"] += 1
            elif u[0] == "CARE" and "animal" in t and not t.get("cared_today"): P["care"] += 1
            elif u[0] == "WATER" and t.get("kind") == "PLANT" and not t.get("watered_today"): P["water"] += 1
            elif u[0] == "FERTILIZE" and t.get("kind") == "PLANT": P["fert"] += 1
            elif u[0] == "COLLECT_FERTILIZER" and t.get("fertilizer_available"): P["H_FERT"] += 1
        if obs[i]["hour"] == 23:
            P["animals"] = sum(1 for row in f["tiles"] for t in row if isinstance(t, dict) and "animal" in t)
            P["plants"] = sum(1 for row in f["tiles"] for t in row if isinstance(t, dict) and t.get("kind") == "PLANT")
            P["straw"] = sum(1 for row in f["tiles"] for t in row if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
            P["unwatered"] = sum(1 for row in f["tiles"] for t in row if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today"))
            P["money"] = int(f["money"])
    g.step(acts[0], acts[1]); step += 1; g.force_shops([n for n, st in sched if st <= step])
print(f"scenario {idx}: V15 {g.reward(0):.0f} vs V10 {g.reward(1):.0f}")
tot = [collections.Counter(), collections.Counter()]
for i in range(2):
    for d in prod[i]:
        for kk, v in prod[i][d].items():
            if kk.startswith("H_") or kk in ("feed", "care", "water", "fert"): tot[i][kk] += v
print("V15 全季收获/动作:", dict(sorted(tot[0].items()))); print("V10 全季收获/动作:", dict(sorted(tot[1].items())))
for d in (2, 5, 8, 11, 14, 17, 20, 23, 26):
    a, b = prod[0][d], prod[1][d]
    print(f"day {d:2d} V15 money {a['money']:6d} an {a['animals']:2d} pl {a['plants']:2d} straw {a['straw']:2d} unwat {a['unwatered']:2d} water {a['water']:2d} fert {a['fert']:2d} | V10 money {b['money']:6d} an {b['animals']:2d} pl {b['plants']:2d} straw {b['straw']:2d} unwat {b['unwatered']:2d} water {b['water']:2d} fert {b['fert']:2d}")
