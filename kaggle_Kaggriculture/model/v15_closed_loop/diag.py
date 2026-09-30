"""V15 诊断：单局 vs V10，逐日状态 + 收入构成 + 劳动分配。用法：diag.py [scenario_idx] [quiet]"""
import sys, json, collections, traceback, os
H = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v4_demand_race/harness"
sys.path.insert(0, H); os.chdir(H)
from engine import fresh_agent, load_scenario
from revenue import settle
W = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture"
def val(x): return x() if callable(x) else x
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0; quiet = len(sys.argv) > 2
sc = json.load(open("scenarios_64.json"))[idx]
c = fresh_agent(f"{W}/model/v15_closed_loop/main.py"); o = fresh_agent(f"{W}/model/v10_rule_distill/dist/main.py")
k = load_scenario(); g = k.Game(seed=sc["seed"]); sched = sc["shops"]; g.force_shops([n for n, st in sched if st <= 0]); step = 0
errs = 0; byday = collections.defaultdict(collections.Counter); moves = {"NORTH","SOUTH","EAST","WEST"}
REV = [collections.Counter(), collections.Counter()]; QTY = [collections.Counter(), collections.Counter()]; SP = [collections.Counter(), collections.Counter()]
def stat(farm):
    an = we = pl = pas = 0
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if "animal" in t: an += 1
                elif t.get("kind") == "WEED": we += 1
                elif t.get("kind") == "PLANT": pl += 1
                elif t.get("kind") in ("PASTURE", "COOP"): pas += 1
    return an, we, pl, pas
while not val(g.done):
    o0, o1 = g.observe(0), g.observe(1)
    try: a0 = c._agent(o0)
    except Exception:
        errs += 1
        if errs <= 3: traceback.print_exc()
        a0 = {"farmer": ["PASS"], "hands": [["PASS"]] * len(o0["farms"][0]["hands"]), "market": []}
    a1 = o.agent(o1); f = o0["farms"][0]; d = o0["day"]
    for u in [a0["farmer"]] + a0["hands"]: byday[d]["move" if u[0] in moves else u[0]] += 1
    if o0["hour"] == 12 and d % 2 == 0 and not quiet:
        sh = o0["private"]["shed"]
        unfed = sum(1 for row in f["tiles"] for t in row if isinstance(t, dict) and "animal" in t and not t.get("fed_today"))
        print(f"day {d:2d} money {f['money']:7.0f} an/we/pl/pas {stat(f)} unfed@12 {unfed} hands {len(f['hands'])} land {len(f['unlocked_quadrants'])} shed {sum(sh.values())} wheat {sh.get('WHEAT',0)} seeds {dict((k,v) for k,v in o0['private']['seeds'].items() if v)} | V10 {o1['farms'][1]['money']:7.0f} {stat(o1['farms'][1])}")
    inv = dict(o0["market"]["inventory"]); sheds = [dict(o0["private"]["shed"]), dict(o1["private"]["shed"])]; moneys = [f["money"], o1["farms"][1]["money"]]
    rev, qty, sp = settle([a0.get("market") or [], a1.get("market") or []], inv, sheds, moneys)
    for i in range(2): REV[i].update(rev[i]); QTY[i].update(qty[i]); SP[i].update(sp[i])
    g.step(a0, a1); step += 1; g.force_shops([n for n, st in sched if st <= step])
print(f"scenario {idx} seed {sc['seed']}: V15 {g.reward(0):.0f} vs V10 {g.reward(1):.0f} ({g.reward(0)-g.reward(1):+.0f}) | errors {errs}")
if not quiet:
    for i, nm in enumerate(("V15", "V10")): print(nm, {k: (QTY[i][k], round(REV[i][k])) for k in QTY[i]}, "支出", dict(SP[i]))
    for d in (0, 3, 6, 9, 12, 18, 24, 28): print(f"  day {d:2d}:", dict(byday[d]))
