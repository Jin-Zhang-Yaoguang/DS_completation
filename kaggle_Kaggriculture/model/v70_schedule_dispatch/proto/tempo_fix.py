"""修正包装层:保持原订单顺序(卖单原位),被推迟的卖单在节拍步放到最前面。"""
import statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full
from sched_f import ExecF
from perturb import play

def tempo3(agent, keep=(0, 1), start_day=0, cap=40, cats=None):
    pend = []
    def f(obs):
        a = agent(obs); t = int(obs.get("step", 0))
        mk = [list(x) for x in (a.get("market") or [])]
        is_sell = lambda x: x and x[0] == "SELL" and (cats is None or (len(x) > 1 and x[1] in cats))
        active = t // 24 >= start_day and t < 690 and t > 2
        if not active or t % 4 in keep:
            out = pend + mk; pend.clear()
        else:
            pend.extend(x for x in mk if is_sell(x)); out = [x for x in mk if not is_sell(x)]
            if len(pend) > cap: del pend[:len(pend) - cap]
        if len(out) > 10:
            # 超出 10 单:优先保留原本本步的非卖单,再补卖单
            non = [x for x in out if not (x and x[0] == "SELL")]; sel = [x for x in out if x and x[0] == "SELL"]
            out = sel[:max(0, 10 - len(non))] + non
        return {"farmer": a.get("farmer"), "hands": a.get("hands"), "market": out}
    return f

VARS = {"全余数(应=带子)": dict(keep=(0, 1, 2, 3)), "节拍{0,1}": dict(), "节拍{1}": dict(keep=(1,)),
        "第10天起 节拍{0,1}": dict(start_day=10), "只对非小麦非肥料": dict(cats={"MILK","WOOL","EGG","STRAWBERRY","MELON","TOMATO","CARROT"})}
def one(job):
    seed, seat, opp, name, base = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    b0, b1 = play(sp.fidelity.make_agent(me), op_spec, seed, seat)
    if base == "tape": ag = sp.fidelity.make_agent(me)
    else: ag = ExecF(record_full(me, op_spec, seed, seat), 0, "xy", "spawn")
    v0, v1 = play(tempo3(ag, **VARS[name]), op_spec, seed, seat)
    return name, base, b0, b0 - b1, v0, v0 - v1
if __name__ == "__main__":
    jobs = [(s, s % 2, o, n, b) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for n in VARS for b in ("tape", "v0f")]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for n in VARS:
        for b in ("tape", "v0f"):
            v = [r for r in res if r[0] == n and r[1] == b]
            print(f"{n:20s} 底座={b:4s} 银行比中位 {statistics.median(r[4]/r[2] for r in v):6.1%} 胜 {sum(r[5]>0 for r in v)}/{len(v)} 分差变化中位 {statistics.median(r[5]-r[3] for r in v):+8.0f}  (带子胜 {sum(r[3]>0 for r in v)})")
