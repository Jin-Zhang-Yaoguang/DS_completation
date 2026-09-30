"""A 方向阶段1:t300 二次路由搜索(train)。扫描 seed2100-2339×3 对手,命中 wk2 表 11 组合的局,
对每局跑 基线(不切) + 6 条候选路线的 t300 切换;记录第 3 家店。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
A = HERE / "agents"
OPPS = {"V43": "kernels_0915/v43_agent.py", "V41": "kernels_0914/v41_agent.py", "V38原版": "kernels_0913/v38_main.py"}
TAB11 = {"BRUNCH_SPOT|BAKERY","FARMERS_MARKET|BAKERY","YARN_STORE|PIZZA_SHOP","YARN_STORE|SMOOTHIE_SHOP","FARMERS_MARKET|YARN_STORE",
         "PET_CAFE|YARN_STORE","BAKERY|SMOOTHIE_SHOP","BRUNCH_SPOT|FARMERS_MARKET","SMOOTHIE_SHOP|BRUNCH_SPOT","YARN_STORE|ICE_CREAM_SHOP","ICE_CREAM_SHOP|PET_CAFE"}
CAND = [107, 110, 112, 118, 120, 126]
def play(sd, seat, opp, rid, stop_at=None):
    os.environ["KAG_T300_ROUTE"] = str(rid)
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{A}/y68wk2t3_main.py"); op = fidelity.make_agent(f"sub:{A}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd); t = 0; shops = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[1-seat] = op(obs[1-seat]); g.step(a[0], a[1]); t += 1
        if t == 220:
            shops = list(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:3])
            if stop_at: return shops, None
    return shops, float(g.reward(seat) - g.reward(1-seat))
def scan(job):
    sd, opp = job
    try:
        sh, _ = play(sd, sd % 2, opp, -1, stop_at=True); return (opp, sd, sh)
    except Exception: return (opp, sd, None)
def ev(job):
    sd, opp, rid = job
    try:
        sh, m = play(sd, sd % 2, opp, rid); return (opp, sh, rid, sd, m)
    except Exception: return (opp, None, rid, sd, None)
if __name__ == "__main__":
    seeds = list(range(2100, 2340))
    with ProcessPoolExecutor(7) as ex:
        sc = list(ex.map(scan, [(sd, o) for sd in seeds for o in OPPS], chunksize=4))
    hits = [(sd, opp, sh) for opp, sd, sh in sc if sh and "|".join(sh[:2]) in TAB11]
    print("命中", len(hits), flush=True)
    jobs = [(sd, opp, rid) for sd, opp, sh in hits for rid in [-1] + CAND]
    print("评估任务", len(jobs), flush=True)
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(ev, jobs, chunksize=4))
    json.dump([list(r) for r in res], open(HERE/"t300_search.json", "w"), ensure_ascii=False)
    print("done")
