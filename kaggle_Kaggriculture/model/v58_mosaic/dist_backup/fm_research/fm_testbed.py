"""FM 线上测试床:207 局含 FM 组合的线上对局,线上 seed+席位,我方=指定版本;
对手:开局 (5,10)/(60)→反应式 V43;(13,30)/(30)→反应式 V38;其他→线上 tape。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
VER = sys.argv[1] if len(sys.argv) > 1 else "y68v"
def opp_mode(op_open):
    op_open = (tuple(op_open[0]), tuple(op_open[1]))
    if op_open == ((5, 10), (60,)): return "v43"
    if op_open == ((13, 30), (30,)): return "v38"
    return "tape"
def one(r):
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{r['ep']}-replay.json"))
    nm = rep["info"]["TeamNames"]; seat = nm.index("datatuu"); o = 1 - seat; st = rep["steps"]
    mode = opp_mode(r["op_open"])
    me = fidelity.make_agent(f"sub:{S}/{VER}_main.py")
    if mode == "tape": op = fidelity.tape_agent([st[t + 1][o].get("action") or {} for t in range(len(st) - 1)])
    else: op = fidelity.make_agent(f"sub:{S}/" + {"v43": "kernels_0915/v43_agent.py", "v38": "kernels_0913/v38_main.py"}[mode])
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"]); t = 0; combo = None; route = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[o] = op(obs[o])
        g.step(acts[0], acts[1]); t += 1
        if t == 146: combo = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
    return dict(r, mode=mode, sim=g.reward(seat) - g.reward(o), sim_combo=combo)
if __name__ == "__main__":
    rows = json.load(open(S / "fm_live_rows.json"))
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, rows, chunksize=2))
    json.dump(res, open(S / f"fm_testbed_{VER}.json", "w"), ensure_ascii=False)
    fm_res = [r for r in res if r["sim_combo"] and "FARMERS_MARKET" in r["sim_combo"].split("|")]
    print(f"[{VER}] 207 局重跑:胜 {sum(r['sim']>0 for r in res)}/{len(res)};其中重跑后组合仍含 FM 的 {len(fm_res)} 局:胜 {sum(r['sim']>0 for r in fm_res)}")
    for mode in ("v43", "v38", "tape"):
        v = [r for r in res if r["mode"] == mode]
        if v: print(f"   对手={mode:4s} {sum(r['sim']>0 for r in v)}/{len(v)} 中位 {statistics.median([r['sim'] for r in v]):+.0f}")
    by = {}
    for r in res: by.setdefault(r["sim_combo"], []).append(r)
    print("   按重跑组合:" + " | ".join(f"{c}:{sum(x['sim']>0 for x in v)}/{len(v)}" for c, v in sorted(by.items(), key=lambda kv: sum(x['sim']>0 for x in kv[1])/len(kv[1]))))
    print("   输局:")
    for r in sorted(res, key=lambda r: r["sim"]):
        if r["sim"] > 0: break
        print(f"     {r['sim']:+8.0f}(线上{r['m']:+7.0f}) vs {r['opp'][:16]:16s} 对手={r['mode']:4s} 线上组合 {r['combo']:30s} 重跑组合 {r['sim_combo']}")
