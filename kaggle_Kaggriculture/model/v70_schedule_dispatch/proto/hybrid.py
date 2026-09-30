"""混合底座:田间指令来自 v0f 执行器,市场单每步由原带子 agent(含规则层)现场生成。三基准:无改动/随机卡人/换胡萝卜/节拍。"""
import statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full
from sched_f import ExecF
from perturb import perturbed, make_plan, play
from swap_bench import swap
from tempo_fix import tempo3

class Hybrid:
    def __init__(self, rec, me_spec):
        self.ex = ExecF(rec, 0, "xy", "spawn"); self.base = sp.fidelity.make_agent(me_spec)
    def __call__(self, obs):
        b = self.base(obs); e = self.ex(obs)
        return {"farmer": e["farmer"], "hands": e["hands"], "market": [list(x) for x in (b.get("market") or [])]}

def build(kind, me, op_spec, seed, seat, rec):
    if kind == "tape": return sp.fidelity.make_agent(me)
    if kind == "v0f": return ExecF(rec, 0, "xy", "spawn")
    return Hybrid(rec, me)

def wrap(bench, ag, seed):
    if bench == "无改动": return ag
    if bench == "卡1步": return perturbed(ag, make_plan(seed, 1, 2))
    if bench == "换胡萝卜25%": return swap(ag, 0.25)
    if bench == "节拍{0,1}": return tempo3(ag)

BENCH = ["无改动", "卡1步", "换胡萝卜25%", "节拍{0,1}"]
def one(job):
    seed, seat, opp, bench, kind = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    v0, v1 = play(wrap(bench, build(kind, me, op_spec, seed, seat, rec), seed), op_spec, seed, seat)
    return bench, kind, rec["bank"][0], rec["bank"][0] - rec["bank"][1], v0, v0 - v1
if __name__ == "__main__":
    jobs = [(s, s % 2, o, b, k) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for b in BENCH for k in ("tape", "v0f", "hybrid")]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for b in BENCH:
        row = []
        for k in ("tape", "v0f", "hybrid"):
            v = [r for r in res if r[0] == b and r[1] == k]
            row.append(f"{k}: 银行 {statistics.median(r[4]/r[2] for r in v):.1%} 胜 {sum(r[5]>0 for r in v)}/{len(v)} 分差 {statistics.median(r[5]-r[3] for r in v):+.0f}")
        print(f"{b:10s} | " + " | ".join(row))
