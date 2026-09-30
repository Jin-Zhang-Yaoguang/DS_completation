"""午夜复位浪费测量：每单位每天「最后一次工作之后」到午夜复位之间的移动步（作废步），K1 vs v2 同局双席位。
另测：早上出门阶段（复位后到当天第一次工作）的移动步。
"""
import sys, statistics, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
IDLE = MOVES | {"PASS", "PICKUP", "DROP"}


def side_waste(acts_by_day):
    """acts_by_day[day][unit] = [(hour, op), ...]"""
    tail = Counter(); head = Counter(); tail_hour = Counter(); total_moves = 0
    for day, units in acts_by_day.items():
        for u, seq in units.items():
            total_moves += sum(1 for _, op in seq if op in MOVES)
            work_idx = [i for i, (_, op) in enumerate(seq) if op not in IDLE]
            if not work_idx:
                head["no_work_day_moves"] += sum(1 for _, op in seq if op in MOVES)
                continue
            first, last = work_idx[0], work_idx[-1]
            head["moves"] += sum(1 for _, op in seq[:first] if op in MOVES)
            for h, op in seq[last + 1:]:
                if op in MOVES:
                    tail["moves"] += 1
                    tail_hour[h] += 1
    return {"total_moves": total_moves, "tail": tail["moves"], "head": head["moves"],
            "nowork": head["no_work_day_moves"], "tail_hour": dict(tail_hour)}


def one(job):
    seed, k1_seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import importlib.util, engine, fidelity
    spec = importlib.util.spec_from_file_location(f'tw_{seed}_{k1_seat}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    opp = fidelity.make_agent(f'sub:{M}/v2_survival_guard/main.py')
    agents = [mod.agent, opp] if k1_seat == 0 else [opp, mod.agent]
    g = engine.load_kagsim().Game(seed=seed)
    rec = [defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list))]
    while not engine._val(g.done):
        o = [g.observe(0), g.observe(1)]
        a = [agents[0](o[0]), agents[1](o[1])]
        day, hour = int(o[0]["day"]), int(o[0]["hour"])
        for s in (0, 1):
            units = [a[s].get("farmer") or ["PASS"]] + list(a[s].get("hands") or [])
            for i, u in enumerate(units):
                rec[s][day][i].append((hour, (u or ["PASS"])[0]))
        g.step(a[0], a[1])
    w = [side_waste(rec[s]) for s in (0, 1)]
    return {"k1": w[k1_seat], "v2": w[1 - k1_seat]}


def main():
    jobs = [(770041 + 229 * i, seat) for i in range(4) for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    for who in ("k1", "v2"):
        med = lambda k: statistics.median(r[who][k] for r in res)
        th = Counter()
        for r in res:
            th.update({int(k): v for k, v in r[who]["tail_hour"].items()})
        print(f"{who}: 总移动 {med('total_moves'):.0f} | 最后工作后作废移动 {med('tail'):.0f} | 出门到首次工作移动 {med('head'):.0f} | "
              f"全天无工作单位的移动 {med('nowork'):.0f}")
        print(f"    作废移动按小时: {sorted(th.items())}")


if __name__ == '__main__':
    main()
