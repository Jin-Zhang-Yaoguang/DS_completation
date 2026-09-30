import statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from perturb import play

def tempo2(agent, keep=(0, 1), start_day=0, cash_floor=None, cap=40, cats=None):
    pend = []
    def f(obs):
        a = agent(obs); t = int(obs.get("step", 0)); p = int(obs.get("player", 0))
        money = obs["farms"][p]["money"]
        mk = list(a.get("market") or [])
        is_sell = lambda x: x and x[0] == "SELL" and (cats is None or (len(x) > 1 and x[1] in cats))
        sells = [x for x in mk if is_sell(x)]; rest = [x for x in mk if not is_sell(x)]
        active = t // 24 >= start_day and t < 690 and not (cash_floor is not None and money < cash_floor)
        if not active or t % 4 in keep:
            out = rest + pend + sells; pend.clear()
        else:
            pend.extend(sells); out = rest
            if len(pend) > cap: del pend[:len(pend) - cap]
        return {"farmer": a.get("farmer"), "hands": a.get("hands"), "market": out[:10]}
    return f

VARS = {
    "全余数(应=带子)": dict(keep=(0, 1, 2, 3)),
    "节拍{0,1}": dict(),
    "第10天起": dict(start_day=10),
    "现金<500不推迟": dict(cash_floor=500),
    "第10天起+现金<2000不推迟": dict(start_day=10, cash_floor=2000),
    "只对非小麦非肥料": dict(cats={"MILK", "WOOL", "EGG", "STRAWBERRY", "MELON", "TOMATO", "CARROT"}),
}
def one(job):
    seed, seat, opp, name = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    b0, b1 = play(sp.fidelity.make_agent(me), op_spec, seed, seat)
    v0, v1 = play(tempo2(sp.fidelity.make_agent(me), **VARS[name]), op_spec, seed, seat)
    return name, b0, b0 - b1, v0, v0 - v1
if __name__ == "__main__":
    jobs = [(s, s % 2, o, n) for s in range(1100, 1104) for o in ("y68s2", "y68r2") for n in VARS]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for n in VARS:
        v = [r for r in res if r[0] == n]
        print(f"{n:22s} 银行比中位 {statistics.median(r[3]/r[1] for r in v):6.1%} 胜 {sum(r[4]>0 for r in v)}/{len(v)} 分差变化中位 {statistics.median(r[4]-r[2] for r in v):+8.0f}  (带子胜 {sum(r[2]>0 for r in v)})")
