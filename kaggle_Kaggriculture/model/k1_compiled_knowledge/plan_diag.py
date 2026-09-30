"""晨间日计划器诊断（单局，ga4 最优 + plan_on 看2，vs y68g）：规划时刻/格数/路线长度/重规划次数、动作来源（计划 vs M3 等）、各时刻任务格数。"""
import sys, json, importlib.util, os
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
sys.path.insert(0, f'{M}/v16_online_fidelity'); sys.path.insert(0, HERE)
import engine, fidelity
from schedule_gen import gen_tables, DEFAULTS
best = max(json.load(open(f'{HERE}/best_iter_ga4.json'))['candidates'], key=lambda c: c['hold_margin'])
params = {**DEFAULTS, **best['params'], 'plan_on': 1, 'plan_look': 2}
spec = importlib.util.spec_from_file_location('pd', f'{HERE}/main.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
ov = gen_tables(params); te = ov.pop('tuning_extra')
ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
mod.KN_OVERRIDE = ov
plans = []
orig = mod._day_plan
def wrapped(st, tu, positions, by_pos, bs):
    tours = orig(st, tu, positions, by_pos, bs)
    ops = Counter(z[3][0] for lst in by_pos.values() for z in lst)
    plans.append((st.get('last_turn', 0), len(positions), len(by_pos), sum(len(t) for t in tours.values()),
                  [len(t) for t in tours.values()], dict(ops)))
    return tours
mod._day_plan = wrapped
opp = fidelity.make_agent(f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py')
g = engine.load_kagsim().Game(seed=930071)
prev_mv = Counter()
tag_by_hour = defaultdict(Counter)
while not engine._val(g.done):
    o0, o1 = g.observe(0), g.observe(1)
    a0 = mod.agent(o0); a1 = opp(o1)
    st = mod._STATE.get(0, {})
    mv = Counter(st.get('mv') or {})
    d = mv - prev_mv
    prev_mv = mv
    day, hour = int(o0['day']), int(o0['hour'])
    if day in (5, 12, 20):
        tag_by_hour[(day, hour)].update(d)
    g.step(a0, a1)
print('终局', o0['farms'][0]['money'], o0['farms'][1]['money'])
for day in (5, 12, 20):
    ps = [p for p in plans if p[0] // 24 == day]
    print(f"\n== d{day}：规划 {len(ps)} 次")
    for t, n, ntile, nplan, lens, ops in ps[:8]:
        print(f"   h{t % 24:2d} 单位{n:2d} 可规划格{ntile:3d} 路线格合计{nplan:3d} 各路线长 {lens} 任务 {ops}")
    for h in (1, 2, 3, 6, 9, 12, 15, 18, 21):
        print(f"   h{h:2d} 移动标签 {dict(tag_by_hour[(day, h)])}")
