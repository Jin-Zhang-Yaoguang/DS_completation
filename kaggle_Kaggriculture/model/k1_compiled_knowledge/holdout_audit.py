"""holdout 污染审计：现池 4 方案 + ga7 均衡最优，分别在 (a) 老 HOLD 口径 (b) 全新 seed 同对手 上重评。"""
import sys, json, os, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['K1_OPP_TIERS'] = 'opp_tiers.json'
import tune_iter as T
from concurrent.futures import ProcessPoolExecutor


def main():
    old = json.load(open('plan_pool.json'))
    ga7 = json.load(open('plan_pool_iter_ga7.json'))
    cands = [[p['params'].get(n, T.DEFAULTS[n]) for n in [x[0] for x in T.SCHED_SPACE]] for p in old[:2] + ga7[:1]]
    names = ['现池#1', '现池#2', 'ga7均衡#1']
    with ProcessPoolExecutor(max_workers=8) as pool:
        hv, hs = T.HOLD_SEEDS[:6], T.HOLD_SEEDS[6:9]
        r_old = T.eval_cands(cands, hv, hs, pool, opps=T.HOLD_OPPS)
        new_seeds = [777001 + 61 * i for i in range(6)]
        r_new = T.eval_cands(cands, new_seeds, [777801, 777862, 777923], pool, opps=T.HOLD_OPPS)
    for n, a, b in zip(names, r_old, r_new):
        print(f"{n:10s} 老holdout margin {a[1]:+8.0f} own {a[2]:7.0f} | 新seed margin {b[1]:+8.0f} own {b[2]:7.0f} | 差 {b[1] - a[1]:+.0f}")


if __name__ == '__main__':
    main()
