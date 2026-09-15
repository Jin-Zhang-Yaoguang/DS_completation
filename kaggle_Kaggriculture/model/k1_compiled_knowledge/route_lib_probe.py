"""路线库可行性探针：Majkel 活跃版本（56156662）回放，按（step, 商店历史前缀）统计各单位众数动作覆盖率。
覆盖率 = 在该键下动作等于众数的局占比；按天报告：无条件 / 按完整商店历史条件（支持局数 ≥ MINSUP）。
"""
import json, sys, os, statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
LS = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/leader_style_20260915'
MINSUP = int(sys.argv[1]) if len(sys.argv) > 1 else 5


def load(ep):
    p = ep['path']
    if not os.path.exists(p):
        alt = f"{LS}/replays/episode-{ep['episode_id']}-replay.json"
        if os.path.exists(alt):
            p = alt
        else:
            return None
    rep = json.load(open(p))
    seat = ep['seat']
    steps = rep.get('steps') or []
    rows = []
    shops_hist = ()
    for t in range(1, len(steps)):
        obs = steps[t - 1][seat].get('observation') or {}
        act = steps[t][seat].get('action') or {}
        shops = tuple((obs.get('town') or {}).get('unlocked_shops') or [])
        units = [json.dumps(act.get('farmer') or ['PASS'])] + [json.dumps(h) for h in (act.get('hands') or [])]
        rows.append((t - 1, shops, units, json.dumps(act.get('market') or [])))
    return ep['episode_id'], rows


def main():
    eps = [e for e in json.load(open(f'{LS}/episode_table.json')) if str(e.get('submission_id')) == '56156662']
    with ProcessPoolExecutor(max_workers=8) as pool:
        data = [d for d in pool.map(load, eps) if d]
    print(f"活跃版本 56156662：清单 {len(eps)} 局，本地可读 {len(data)} 局")
    # 键：step 或 (step, shops)
    uncond = defaultdict(Counter); cond = defaultdict(Counter)
    uncond_m = defaultdict(Counter); cond_m = defaultdict(Counter)
    for _, rows in data:
        for t, shops, units, market in rows:
            for u, a in enumerate(units):
                uncond[(t, u)][a] += 1
                cond[(t, shops, u)][a] += 1
            uncond_m[t][market] += 1
            cond_m[(t, shops)][market] += 1
    per_day = defaultdict(lambda: Counter())
    for (t, u), c in uncond.items():
        d = t // 24
        n = sum(c.values())
        per_day[d]['u_hit'] += c.most_common(1)[0][1]
        per_day[d]['u_n'] += n
        if u == 0:
            per_day[d]['f_hit'] += c.most_common(1)[0][1]
            per_day[d]['f_n'] += n
    for (t, shops, u), c in cond.items():
        d = t // 24
        n = sum(c.values())
        if n >= MINSUP:
            per_day[d]['c_hit'] += c.most_common(1)[0][1]
            per_day[d]['c_n'] += n
        per_day[d]['c_all'] += n
    for t, c in uncond_m.items():
        d = t // 24
        per_day[d]['m_hit'] += c.most_common(1)[0][1]
        per_day[d]['m_n'] += sum(c.values())
    for (t, shops), c in cond_m.items():
        d = t // 24
        n = sum(c.values())
        if n >= MINSUP:
            per_day[d]['cm_hit'] += c.most_common(1)[0][1]
            per_day[d]['cm_n'] += n
    print(f"按天：单位动作=众数的占比（无条件 / 同商店历史且支持≥{MINSUP} 的键内，括号内=被此类键覆盖的单位步占比）；农夫；市场")
    for d in range(30):
        r = per_day[d]
        if not r['u_n']:
            continue
        print(f"  d{d + 1:2d} 单位 无条件 {r['u_hit'] / r['u_n']:.2f} | 同商店 {r['c_hit'] / max(1, r['c_n']):.2f} ({r['c_n'] / max(1, r['c_all']):.2f}) | "
              f"农夫 {r['f_hit'] / max(1, r['f_n']):.2f} | 市场 无条件 {r['m_hit'] / r['m_n']:.2f} 同商店 {r['cm_hit'] / max(1, r['cm_n']):.2f}")


if __name__ == '__main__':
    main()
