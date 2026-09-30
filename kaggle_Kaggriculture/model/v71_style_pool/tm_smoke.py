import sys, json, glob
from pathlib import Path
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
import fidelity, engine
hits = []
for fn in sorted(glob.glob(str(HERE/"wk5live"/"episode-*.json"))):
    r = json.load(open(fn)); nm = r["info"]["TeamNames"]
    if nm.count("datatuu") != 1: continue
    s = r["steps"]
    shops = (s[360][0]["observation"].get("town") or {}).get("unlocked_shops") or []
    if sum(x in ("PIZZA_SHOP", "FARMERS_MARKET") for x in shops) >= 2: hits.append(fn)
print("命中局", len(hits))
for fn in hits[:4]:
    r = json.load(open(fn)); nm = r["info"]["TeamNames"]; s = r["steps"]
    seat = nm.index("datatuu"); o = 1 - seat
    for ver in ("y68wk5", "y68tm"):
        op = fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
        me = fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
        k = engine.load_kagsim(); g = k.Game(seed=r["info"]["seed"]); t = 0; tom = 0
        while not engine._val(g.done):
            obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o])
            for c in [a[seat].get("farmer")] + list(a[seat].get("hands") or []):
                if c and c[:2] == ["PLANT", "TOMATO"]: tom += 1
            g.step(a[0], a[1]); t += 1
        print(f"  {Path(fn).name[:24]} vs {nm[o][:12]:12s} {ver:7s} margin {g.reward(seat)-g.reward(o):+9.0f} 种番茄 {tom}  (线上 {r['rewards'][seat]-r['rewards'][o]:+.0f})")
