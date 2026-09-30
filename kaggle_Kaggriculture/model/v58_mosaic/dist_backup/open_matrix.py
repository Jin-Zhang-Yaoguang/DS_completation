"""开局对撞支付矩阵:双方各选 t1 开局 (买单列表, 卖单列表),V38 底盘跑到 t30,
记录 day1 帮工到位数与现金。目标:找支配性开局。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent

# 策略空间(V38 原版 t1 = 买13+30 / 卖30)
STRATS = {
    "v38":  [["BUY_PRODUCT","WHEAT",13],["BUY_PRODUCT","WHEAT",30],["SELL","WHEAT",30]],
    "g17":  [["BUY_PRODUCT","WHEAT",13],["BUY_PRODUCT","WHEAT",17],["SELL","WHEAT",30]],
    "i43":  [["BUY_PRODUCT","WHEAT",43],["SELL","WHEAT",20],["SELL","WHEAT",22]],
    "v42":  [["BUY_PRODUCT","WHEAT",5],["BUY_PRODUCT","WHEAT",10],["SELL","WHEAT",60]],
    "s99":  [["SELL","WHEAT",99]],
    "b0s30":[["SELL","WHEAT",30]],
    "b13s42":[["BUY_PRODUCT","WHEAT",13],["SELL","WHEAT",20],["SELL","WHEAT",22]],
    "null": [],
}

def make(tag):
    p = S / f"om_{tag}_main.py"
    if not p.exists():
        src = (S / "kernels_0913" / "v38_main.py").read_text()
        src += f'''

_OM_BASE = agent
_OM_DONE = [False]

def _om_agent(observation, configuration=None):
    act = _OM_BASE(observation, configuration)
    try:
        if not _OM_DONE[0]:
            step = int(observation.get("step", 0))
            mkt = act.get("market") or []
            sig = [(o[0], o[1] if len(o) > 1 else None) for o in mkt if o]
            if ("BUY_PRODUCT", "WHEAT") in sig and ("SELL", "WHEAT") in sig and step <= 2:
                act["market"] = {json.dumps(STRATS[tag])}
                _OM_DONE[0] = True
            if step > 4:
                _OM_DONE[0] = True
    except Exception:
        pass
    return act

_OM_ENTRY = _om_agent
'''
        p.write_text(src)
    return p

def one(job):
    a, b, sd = job
    sys.path.insert(0, str(M / "v16_online_fidelity"))
    sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    a0 = fidelity.make_agent(f"sub:{S}/om_{a}_main.py")
    a1 = fidelity.make_agent(f"sub:{S}/om_{b}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    out = {}
    for step in range(72):
        g.step(a0(g.observe(0)), a1(g.observe(1)))
        if step == 27:
            fs = g.observe(0)["farms"]
            out["hands"] = (len(fs[0].get("hands") or []), len(fs[1].get("hands") or []))
            out["money"] = (round(fs[0].get("money") or 0), round(fs[1].get("money") or 0))
    fs = g.observe(0)["farms"]
    out["money72"] = (round(fs[0].get("money") or 0), round(fs[1].get("money") or 0))
    return a, b, sd, out

if __name__ == "__main__":
    for t in STRATS: make(t)
    names = list(STRATS)
    jobs = [(a, b, sd) for a in names for b in names if a <= b for sd in (500, 1108)]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=2))
    print(f"{'A':8s}{'B':8s}{'sd':>5s}  A工/B工  A钱/B钱@d1  A钱/B钱@d3")
    for a, b, sd, o in res:
        print(f"{a:8s}{b:8s}{sd:5d}  {o['hands'][0]}/{o['hands'][1]}   {o['money'][0]:>4d}/{o['money'][1]:<4d}  {o['money72'][0]:>5d}/{o['money72'][1]:<5d}")
