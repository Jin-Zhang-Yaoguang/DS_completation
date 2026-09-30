import sys, statistics
from concurrent.futures import ProcessPoolExecutor
def one(job):
    seed, seat, opp = job
    import sched_proto as sp
    rec = sp.record(f"sub:{sp.S}/y68x3b13_main.py", f"sub:{sp.S}/{opp}_main.py", seed, seat)
    b0, b1, st, left = sp.run_exec(rec, f"sub:{sp.S}/{opp}_main.py", seed, seat, 0)
    return seed, seat, opp, rec["bank"][0], rec["bank"][0]-rec["bank"][1], b0, b0-b1, st.get("late",0), left
if __name__ == "__main__":
    jobs = [(s, s % 2, o) for s in range(1100, 1108) for o in ("y68s2", "y68r2")]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for r in res: print(f"seed{r[0]} seat{r[1]} vs {r[2]:6s} 带子银行 {r[3]:7.0f} 分差 {r[4]:+7.0f} | 执行器银行 {r[5]:7.0f} ({r[5]/r[3]:.1%}) 分差 {r[6]:+7.0f} 迟到 {r[7]} 剩余 {r[8]}")
    ratio = [r[5]/r[3] for r in res]
    print(f"银行比 中位 {statistics.median(ratio):.1%} 最低 {min(ratio):.1%};带子胜 {sum(r[4]>0 for r in res)}/{len(res)},执行器胜 {sum(r[6]>0 for r in res)}/{len(res)};分差变化中位 {statistics.median(r[6]-r[4] for r in res):+.0f}")
