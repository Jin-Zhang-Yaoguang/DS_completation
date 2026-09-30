"""节拍卖出基准:原带子+节拍层(y68tempo) vs v0f 执行器+同一节拍规则。"""
import collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full
from sched_f import ExecF
from perturb import play

def tempo(agent, keep=(0, 1), cap=40):
    pend = []
    def f(obs):
        a = agent(obs); t = int(obs.get("step", 0))
        mk = list(a.get("market") or [])
        sells = [x for x in mk if x and x[0] == "SELL"]; rest = [x for x in mk if not (x and x[0] == "SELL")]
        if t >= 690 or t % 4 in keep:
            out = rest + pend + sells; pend.clear()
        else:
            pend.extend(sells); out = rest
            if len(pend) > cap: del pend[:len(pend) - cap]
        return {"farmer": a.get("farmer"), "hands": a.get("hands"), "market": out[:10]}
    return f

def one(job):
    seed, seat, opp = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    a0, a1 = play(sp.fidelity.make_agent(f"sub:{sp.S}/y68tempo_main.py"), op_spec, seed, seat)
    b0, b1 = play(tempo(ExecF(rec, 0, "xy", "spawn")), op_spec, seed, seat)
    c0, c1 = play(tempo(sp.fidelity.make_agent(me)), op_spec, seed, seat)
    return seed, opp, rec["bank"][0], rec["bank"][0]-rec["bank"][1], a0, a0-a1, b0, b0-b1, c0, c0-c1

if __name__ == "__main__":
    jobs = [(s, s % 2, o) for s in range(1100, 1106) for o in ("y68s2", "y68r2")]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for r in res: print(f"seed{r[0]} vs {r[1]:6s} 带子 {r[2]:7.0f} {r[3]:+7.0f} | 带子+节拍层(文件) {r[4]:7.0f} {r[5]:+8.0f} | 带子+节拍包装 {r[8]:7.0f} {r[9]:+8.0f} | v0f+节拍 {r[6]:7.0f} {r[7]:+8.0f}")
    def s(i, j): return statistics.median(r[i]/r[2] for r in res), sum(r[j] > 0 for r in res), statistics.median(r[j]-r[3] for r in res)
    for name, i, j in (("带子+节拍层(y68tempo)", 4, 5), ("带子+节拍包装", 8, 9), ("v0f+节拍", 6, 7)):
        a = s(i, j); print(f"{name:18s}: 银行比中位 {a[0]:.1%} 胜 {a[1]}/{len(res)} 分差变化中位 {a[2]:+.0f}")
    print(f"原带子 胜 {sum(r[3] > 0 for r in res)}/{len(res)}")
