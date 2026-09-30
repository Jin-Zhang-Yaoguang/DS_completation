"""BRUNCH|FM 对 V41 大输局拆解:seed3045/3314 座位 0,y68x3(route110)vs y68v(旧路线),分段钱差/工人/仓储/卖出。"""
import sys, json, importlib.util
from pathlib import Path
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def one(job):
    sd, seat, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    spec = importlib.util.spec_from_file_location(f"b{sd}{ver}", f"{S}/{ver}_main.py")
    mm = importlib.util.module_from_spec(spec); spec.loader.exec_module(mm)
    me = [v for k, v in vars(mm).items() if callable(v) and not k.startswith("__")][-1]
    op = fidelity.make_agent(f"sub:{S}/kernels_0914/v41_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd); seg = []; prev = 0; route = None; sells = Counter(); osells = Counter()
    for t in range(720):
        if engine._val(g.done): break
        a = me(g.observe(seat)); b = op(g.observe(1 - seat))
        for x in a.get("market") or []:
            if x and x[0] == "SELL" and len(x) > 2: sells[x[1]] += int(x[2])
        acts = [None, None]; acts[seat] = a; acts[1 - seat] = b
        g.step(acts[0], acts[1])
        if t == 150: route = (mm._IMPL.chassis.players.get(seat) or {}).get("route")
        if (t + 1) % 72 == 0:
            ob = g.observe(seat); f = ob["farms"]
            d = (f[seat].get("money") or 0) - (f[1 - seat].get("money") or 0)
            shed = sum(int(v) for v in ((ob.get("private") or {}).get("shed") or {}).values())
            seg.append(f"d{(t+1)//24}:{d-prev:+.0f}(工{1+len(f[seat].get('hands') or [])}v{1+len(f[1-seat].get('hands') or [])} 仓{shed})")
            prev = d
    return sd, ver, route, g.reward(seat) - g.reward(1 - seat), seg
if __name__ == "__main__":
    jobs = [(sd, 0, v) for sd in (3045, 3314) for v in ("y68x3", "y68v")]
    with ProcessPoolExecutor(4) as ex:
        for sd, ver, route, m, seg in ex.map(one, jobs):
            print(f"\nseed{sd} {ver}: route {route} margin {m:+.0f}")
            print("   " + " ".join(seg))
