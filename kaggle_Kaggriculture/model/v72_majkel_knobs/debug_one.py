"""单局调试:候选包 vs 对手,逐日资金/仓库总量/卖单量,旋钮层异常计数与首个异常。"""
import sys, json, traceback, collections
from pathlib import Path
MODEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
import engine, fidelity

def load(pack):
    ns = {}; exec(compile(Path(pack).read_text(), str(pack), "exec"), ns)
    err = {"n": 0, "first": None, "calls": 0}
    if "_mj_layer" in ns:
        orig = ns["_mj_layer"]
        def wrapped(obs, act):
            err["calls"] += 1
            try: return orig(obs, act)
            except Exception:
                err["n"] += 1
                if err["first"] is None: err["first"] = (int(obs["step"]), traceback.format_exc()[-900:])
                raise
        ns["_mj_layer"] = wrapped
    fns = [v for k, v in ns.items() if callable(v) and not k.startswith("__")]
    return fns[-1], err

def play(pack, opp_spec, seed):
    ag, err = load(pack); opp = fidelity.make_agent(opp_spec)
    g = engine.load_kagsim().Game(seed=seed); fb = {"farmer": ["PASS"], "hands": [], "market": []}
    daily = []
    sells = collections.Counter()
    for t in range(719):
        o0 = g.observe(0)
        if t % 24 == 0:
            shed = (o0.get("private") or {}).get("shed") or {}
            daily.append((t // 24, int(o0["farms"][0]["money"]), sum(v for k, v in shed.items() if k in ("WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER")), sum(sells.values())))
            sells = collections.Counter()
        try: a = ag(o0)
        except Exception: a = dict(fb)
        try: b = opp(g.observe(1))
        except Exception: b = dict(fb)
        for o in a.get("market") or []:
            if o and o[0] == "SELL" and len(o) > 2: sells[o[1]] += int(o[2])
        g.step(a, b)
    return float(g.reward(0)), float(g.reward(1)), daily, err

if __name__ == "__main__":
    opp = "tape:" + str(MODEL / "opponent_pool_v1/tapes/ymg_slice0.json"); seed = 1009
    for label, pack in [("parent", "y68f_parent.py"), ("beat0", "cands/mj_e161725f7a.py"), ("beat1", "cands/mj_d7c68d9250.py"), ("fert45", "cands/mj_f016ffc970.py")]:
        me, op, daily, err = play(pack, opp, seed)
        print(f"== {label}: bank {me:.0f} vs {op:.0f} margin {me-op:+.0f} | layer calls {err['calls']} exceptions {err['n']}")
        if err["first"]: print("   first exception at step", err["first"][0], "\n", err["first"][1])
        print("   day money shed sold(prev day):", [d for d in daily if d[0] % 3 == 0 or d[0] >= 27])
