"""BRUNCH|FM 对 V43 结构拆解:y68x 与 fr_110 各 3 个输/赢 seed,分段钱差、工人、仓储、对手路线。"""
import sys, json, importlib.util
from pathlib import Path
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
    spec2 = importlib.util.spec_from_file_location(f"o{sd}{ver}", f"{S}/kernels_0915/v43_agent.py")
    mo = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(mo)
    op = mo.agent
    k = engine.load_kagsim(); g = k.Game(seed=sd); seg = []; prev = 0
    for t in range(720):
        if engine._val(g.done): break
        acts = [None, None]; acts[seat] = me(g.observe(seat)); acts[1 - seat] = op(g.observe(1 - seat))
        g.step(acts[0], acts[1])
        if (t + 1) % 72 == 0:
            ob = g.observe(seat); f = ob["farms"]
            d = (f[seat].get("money") or 0) - (f[1 - seat].get("money") or 0)
            shed = sum(int(v) for v in ((ob.get("private") or {}).get("shed") or {}).values())
            seg.append(f"d{(t+1)//24}:{d-prev:+.0f}(工{1+len(f[seat].get('hands') or [])}v{1+len(f[1-seat].get('hands') or [])} 仓{shed})")
            prev = d
    my_route = (mm._IMPL.chassis.players.get(seat) or {}).get("route")
    op_route = (mo._IMPL.chassis.players.get(1 - seat) or {}).get("route")
    return sd, seat, ver, my_route, op_route, g.reward(seat) - g.reward(1 - seat), seg
if __name__ == "__main__":
    seeds = json.load(open(S / "combo_seeds_y68v_b.json"))["BRUNCH_SPOT|FARMERS_MARKET"][:4]
    jobs = [(sd, i % 2, v) for i, sd in enumerate(seeds) for v in ("y68x", "fr_110")]
    with ProcessPoolExecutor(8) as ex:
        for sd, seat, ver, mr, orr, m, seg in ex.map(one, jobs):
            print(f"\nseed{sd} seat{seat} {ver}: 我方 route {mr} / 对手 V43 route {orr} margin {m:+.0f}")
            print("   " + " ".join(seg))
