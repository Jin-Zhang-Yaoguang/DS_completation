"""回放跟随 bug 定位：同一观测喂纯 tape 与 K1(eps PASS修复 不切换)，执行纯 tape 动作，打印前若干处输出差异。"""
import sys, json, gzip, importlib.util, os
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
sys.path.insert(0, f'{M}/v16_online_fidelity')
sys.path.insert(0, HERE)
import engine, fidelity
from schedule_gen import gen_tables, DEFAULTS

lib = json.loads(gzip.open(f'{HERE}/route_eps.json.gz').read().decode())
tape = fidelity.tape_agent(lib['eps'][lib['default']])
best = max(json.load(open(f'{HERE}/best_iter_ga4.json'))['candidates'], key=lambda c: c['hold_margin'])
params = {**DEFAULTS, **best['params'], 'eps_on': 1, 'eps_pass': 1, 'eps_repair': 1, 'eps_switch1': 0, 'eps_switch2': 0}
spec = importlib.util.spec_from_file_location('ed', f'{HERE}/main.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
ov = gen_tables(params); te = ov.pop('tuning_extra')
ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
mod.KN_OVERRIDE = ov
opp = fidelity.make_agent(f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py')
g = engine.load_kagsim().Game(seed=700001)
shown = 0
t = 0
while not engine._val(g.done) and shown < 12:
    o0, o1 = g.observe(0), g.observe(1)
    at = tape(o0)
    try:
        ak = mod._decide(o0, None)
        err = None
    except Exception as e:
        import traceback
        ak = None
        err = traceback.format_exc().splitlines()[-3:]
    if err or json.dumps(at, sort_keys=True) != json.dumps(ak, sort_keys=True):
        print(f"t={t} day={o0['day']} hour={o0['hour']} money={o0['farms'][0]['money']}")
        if err:
            print("   K1 异常:", err)
        else:
            for key in ('farmer', 'hands', 'market'):
                if at.get(key) != ak.get(key):
                    print(f"   {key}: tape={at.get(key)} | k1={ak.get(key)}")
        shown += 1
    g.step(at, opp(o1))
    t += 1
print("终局 tape 执行下金币", o0['farms'][0]['money'])
