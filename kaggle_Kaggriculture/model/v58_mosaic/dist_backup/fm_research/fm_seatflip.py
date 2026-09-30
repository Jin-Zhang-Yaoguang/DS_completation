"""y68x3 剩余 9 个 FM 输局换座位复测:原座位 vs 另一座位的 margin 与真实组合。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OPPS = {"V43": "kernels_0915/v43_agent.py", "V41": "kernels_0914/v41_agent.py", "V43+B10": "kernels_0915/v43b10_agent.py"}
def one(job):
    sd, seat, opp = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/y68x3_main.py"); op = fidelity.make_agent(f"sub:{S}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd); t = 0; combo = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1]); t += 1
        if t == 146: combo = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
    return sd, seat, opp, combo, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    res = json.load(open(S / "fm_validate2_y68x3.json"))
    losses = [(r[0], r[1], r[3], r[4], r[5]) for r in res if r[4] and "FARMERS_MARKET" in r[4].split("|") and r[5] <= 0]
    jobs = [(sd, 1 - seat, opp) for sd, seat, opp, combo, m in losses]
    with ProcessPoolExecutor(8) as ex:
        flip = {(sd, opp): (c, m) for sd, seat, opp, c, m in ex.map(one, jobs)}
    real_loss = 0
    for sd, seat, opp, combo, m in sorted(losses, key=lambda x: x[3]):
        c2, m2 = flip[(sd, opp)]
        verdict = "两座位都输(真漏洞)" if m2 <= 0 else "换座位即赢(座位偏置)"
        real_loss += m2 <= 0
        print(f"{combo:32s} seed{sd} vs {opp:8s} 座位{seat}:{m:+6.0f} | 座位{1-seat}:{m2:+6.0f}(组合 {c2}) → {verdict}")
    print(f"\n9 个输局中,两座位都输的真漏洞 {real_loss} 个")
