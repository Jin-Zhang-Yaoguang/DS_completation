"""Majkel 路线库：键（step, 商店前缀层级）→ 各单位槽众数动作 + 众数市场指令，逐级回退。
层级：L2 = 前两家商店（按解锁顺序）、L1 = 第一家商店、L0 = 无条件。只保留支持局数 ≥ MINSUP 且众数占比 ≥ MINSHARE 的条目。
产物：route_lib.json（knowledge 数据，K1 内核 library 模式读取）；打印按天覆盖率。
用法: /opt/anaconda3/bin/python3 build_route_lib.py [minsup] [minshare]
"""
import json, sys, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
LS = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/leader_style_20260915'
HERE = os.path.dirname(os.path.abspath(__file__))
MINSUP = int(sys.argv[1]) if len(sys.argv) > 1 else 8
MINSHARE = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5


def load(ep):
    p = ep['path'] if os.path.exists(ep['path']) else f"{LS}/replays/episode-{ep['episode_id']}-replay.json"
    rep = json.load(open(p))
    seat = ep['seat']
    steps = rep.get('steps') or []
    rows = []
    for t in range(1, len(steps)):
        obs = steps[t - 1][seat].get('observation') or {}
        act = steps[t][seat].get('action') or {}
        shops = list((obs.get('town') or {}).get('unlocked_shops') or [])
        units = [json.dumps(act.get('farmer') or ['PASS'])] + [json.dumps(h) for h in (act.get('hands') or [])]
        rows.append((t - 1, shops[:2], units, json.dumps(act.get('market') or [])))
    return rows


def key(level, t, shops):
    if level == 2:
        return f"{t}|{','.join(shops[:2])}" if len(shops) >= 2 else None
    if level == 1:
        return f"{t}|{shops[0]}" if shops else None
    return f"{t}|"


def main():
    eps = [e for e in json.load(open(f'{LS}/episode_table.json')) if str(e.get('submission_id')) == '56156662']
    with ProcessPoolExecutor(max_workers=8) as pool:
        data = list(pool.map(load, eps))
    units = {lv: defaultdict(lambda: defaultdict(Counter)) for lv in (2, 1, 0)}
    market = {lv: defaultdict(Counter) for lv in (2, 1, 0)}
    n_units = {lv: defaultdict(Counter) for lv in (2, 1, 0)}
    for rows in data:
        for t, shops, us, mk in rows:
            for lv in (2, 1, 0):
                k = key(lv, t, shops)
                if k is None:
                    continue
                for u, a in enumerate(us):
                    units[lv][k][u][a] += 1
                market[lv][k][mk] += 1
                n_units[lv][k][len(us)] += 1
    lib = {"meta": {"source": "Majkel1337 submission 56156662", "games": len(data), "minsup": MINSUP, "minshare": MINSHARE},
           "levels": {}}
    for lv in (2, 1, 0):
        out = {}
        for k, per_u in units[lv].items():
            ent = {"u": {}, "sup": sum(market[lv][k].values())}
            if ent["sup"] < MINSUP:
                continue
            for u, c in per_u.items():
                a, cnt = c.most_common(1)[0]
                tot = sum(c.values())
                if tot >= MINSUP and cnt / tot >= MINSHARE:
                    ent["u"][str(u)] = [json.loads(a), round(cnt / tot, 3)]
            ma, mc = market[lv][k].most_common(1)[0]
            if mc / ent["sup"] >= MINSHARE:
                ent["m"] = [json.loads(ma), round(mc / ent["sup"], 3)]
            ent["hands"] = n_units[lv][k].most_common(1)[0][0] - 1
            out[k] = ent
        lib["levels"][str(lv)] = out
    json.dump(lib, open(f'{HERE}/route_lib.json', 'w'))
    print(f"route_lib.json 写出：L2 {len(lib['levels']['2'])} 键 / L1 {len(lib['levels']['1'])} / L0 {len(lib['levels']['0'])}，"
          f"大小 {os.path.getsize(f'{HERE}/route_lib.json') / 1e6:.1f} MB")
    # 覆盖率：对每局每步每单位，按 L2→L1→L0 回退找到的库动作是否等于实际动作
    per_day = defaultdict(Counter)
    for rows in data:
        for t, shops, us, mk in rows:
            d = t // 24
            for u, a in enumerate(us):
                hit_lv = None
                for lv in (2, 1, 0):
                    k = key(lv, t, shops)
                    ent = lib["levels"][str(lv)].get(k) if k else None
                    if ent and str(u) in ent["u"]:
                        hit_lv = lv
                        per_day[d][f"has{lv}"] += 1
                        per_day[d]["match"] += int(json.dumps(ent["u"][str(u)][0]) == a)
                        break
                per_day[d]["n"] += 1
                if hit_lv is None:
                    per_day[d]["none"] += 1
    print("按天：库有条目占比（L2/L1/L0/无） | 库动作=实际动作占比（占全部单位步）")
    for d in range(30):
        r = per_day[d]
        n = max(1, r["n"])
        print(f"  d{d + 1:2d} L2 {r['has2'] / n:.2f} L1 {r['has1'] / n:.2f} L0 {r['has0'] / n:.2f} 无 {r['none'] / n:.2f} | 命中 {r['match'] / n:.2f}")


if __name__ == '__main__':
    main()
