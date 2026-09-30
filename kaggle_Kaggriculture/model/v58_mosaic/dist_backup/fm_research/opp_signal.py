"""可观测性:y68v 对各类对手,第 1~2 步观测到的对手现金/市场麦库存/麦价;以及第 24、144 步对手帮工与已种地块。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OPPS = {"V38原版": "kernels_0913/v38_main.py", "V41": "kernels_0914/v41_agent.py", "V43": "kernels_0915/v43_agent.py",
        "V43+B10": "kernels_0915/v43b10_agent.py", "qq型": "opp_qq_main.py", "V43+13/13": "opp_v43_1313_main.py"}
def one(job):
    opp, sd, seat = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/y68v_main.py"); op = fidelity.make_agent(f"sub:{S}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd); rec = {}
    for t in range(146):
        ob = g.observe(seat)
        if t in (1, 2, 24, 144):
            f = ob["farms"]; mk = ob.get("market") or {}
            planted = sum(1 for row in f[1 - seat].get("tiles") or [] for tl in row if isinstance(tl, dict) and tl.get("kind") == "PLANT")
            rec[t] = (round(f[1 - seat].get("money") or 0), (mk.get("inventory") or {}).get("WHEAT"), (mk.get("prices") or {}).get("WHEAT"),
                      len(f[1 - seat].get("hands") or []), planted, round(f[seat].get("money") or 0))
        acts = [None, None]; acts[seat] = me(g.observe(seat)); acts[1 - seat] = op(g.observe(1 - seat))
        g.step(acts[0], acts[1])
    return opp, sd, seat, rec
if __name__ == "__main__":
    seeds = [3001, 3107, 3162, 3500]
    jobs = [(o, sd, i % 2) for o in OPPS for i, sd in enumerate(seeds)]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    print(f"{'对手':10s} {'seed':>5s} | t1:对手钱 麦库存 麦价 | t2:对手钱 麦库存 | t24:对手钱 帮工 种地 | t144:对手钱 种地 | t1我钱")
    for opp, sd, seat, r in res:
        print(f"{opp:10s} {sd:5d} | {r[1][0]:5d} {r[1][1]:5d} {r[1][2]:3d} | {r[2][0]:5d} {r[2][1]:5d} | {r[24][0]:5d} {r[24][3]:2d} {r[24][4]:3d} | {r[144][0]:5d} {r[144][4]:3d} | {r[1][5]}")
