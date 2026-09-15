"""对手早期签名：对手层 11 个对手 vs 回放（默认整局 tape），记录对手在 d0-d2 每天 h23 的可观测特征：
单位数、各作物格、动物数、建筑格、金币、单位离仓平均距离、前 48 步对手位置序列哈希（按步）。看能否在 d1/d2 区分对手身份。"""
import sys, json, gzip, os, hashlib, statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
TJ = json.load(open(f'{HERE}/opp_tiers.json'))
FMT = lambda x: x.replace('{M}', TJ['M']).replace('{K1}', TJ['K1'])
OPPS = [(tier, FMT(o)) for tier, t in TJ['tiers'].items() for o in t['opps'][:(3 if tier == 'hard' else 2)]]
M = TJ['M']


def feat(farm, day, hour):
    c = Counter()
    for row in farm.get('tiles') or []:
        for t in row:
            if isinstance(t, dict):
                if t.get('kind') == 'PLANT':
                    c['crop_' + t['crop']] += 1
                elif t.get('animal'):
                    c['an_' + t['animal']] += 1
                elif t.get('kind') in ('PASTURE', 'COOP'):
                    c['struct'] += 1
    c['hands'] = len(farm.get('hands') or [])
    c['money'] = int(farm.get('money', 0))
    return {f"d{day}h{hour}_{k}": v for k, v in c.items()}


def one(job):
    tier, spec_o, seed, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    lib = json.loads(gzip.open(f'{HERE}/route_eps.json.gz').read().decode())
    me = fidelity.tape_agent(lib['eps'][lib['default']])
    opp = fidelity.make_agent(spec_o)
    agents = [me, opp] if seat == 0 else [opp, me]
    g = engine.load_kagsim().Game(seed=seed)
    out = {}
    seqs = []
    t = 0
    while not engine._val(g.done) and t < 73:
        o = [g.observe(0), g.observe(1)]
        a = [agents[0](o[0]), agents[1](o[1])]
        of = o[seat]['farms'][1 - seat]
        day, hour = int(o[0]['day']), int(o[0]['hour'])
        if hour in (11, 23):
            out.update(feat(of, day, hour))
        seqs.append(json.dumps([of.get('farmer')] + list(of.get('hands') or [])))
        if t in (6, 12, 24, 48, 72):
            out[f"pos_hash_t{t}"] = hashlib.md5(''.join(seqs).encode()).hexdigest()[:8]
        g.step(a[0], a[1])
        t += 1
    return tier, spec_o, seed, seat, out


def main():
    jobs = [(t, o, s, seat) for t, o in OPPS for s in (710003, 710134, 710265) for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    json.dump(res, open(f'{HERE}/opp_early_sig_result.json', 'w'))
    keys = ["d0h11_hands", "d0h11_money", "d0h23_hands", "d0h23_money", "d0h23_an_COW", "d0h23_an_SHEEP", "d0h23_struct",
            "d0h23_crop_WHEAT", "d0h23_crop_MELON", "d0h23_crop_STRAWBERRY", "d1h23_hands", "d1h23_money",
            "d1h23_an_COW", "d1h23_an_SHEEP", "d1h23_crop_WHEAT", "d1h23_crop_MELON", "d1h23_crop_STRAWBERRY",
            "d2h23_money", "d2h23_crop_STRAWBERRY", "d2h23_an_COW"]
    print(f"{'对手':38s} " + " ".join(k.replace('_crop_', '_').replace('_an_', '_')[:12].rjust(12) for k in keys))
    for tier, o in OPPS:
        rr = [r[4] for r in res if r[1] == o]
        nm = (o.split('/')[-2] if o.endswith('main.py') else o.split('/')[-1])[:30]
        vals = []
        for k in keys:
            v = [x.get(k, 0) for x in rr]
            vals.append(f"{min(v)}-{max(v)}" if min(v) != max(v) else str(v[0]))
        print(f"{tier[:5]:5s} {nm:32s} " + " ".join(s.rjust(12) for s in vals))
    print("\n前 t 步对手位置序列哈希（不同 seed/席位是否一致 → 可当指纹）:")
    for tier, o in OPPS:
        rr = [r[4] for r in res if r[1] == o]
        nm = (o.split('/')[-2] if o.endswith('main.py') else o.split('/')[-1])[:30]
        print(f"  {nm:32s} " + " ".join(f"t{t}:{len(set(x.get(f'pos_hash_t{t}') for x in rr))}" for t in (6, 12, 24, 48, 72)))


if __name__ == '__main__':
    main()
