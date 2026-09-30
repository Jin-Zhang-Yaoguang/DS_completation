"""Majkel 381 局商店解锁序列分布：各前缀长度的不同序列数与最大组局数；以及同一 kagsim seed 在不同对手下商店序列是否相同（商店是否内生于双方行为）。"""
import json, os, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
LS = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/leader_style_20260915'
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'


def seq_of(ep):
    p = ep['path'] if os.path.exists(ep['path']) else f"{LS}/replays/episode-{ep['episode_id']}-replay.json"
    rep = json.load(open(p))
    seq, times = [], []
    for t, st in enumerate(rep['steps']):
        sh = ((st[ep['seat']].get('observation') or {}).get('town') or {}).get('unlocked_shops') or []
        if len(sh) > len(seq):
            seq = list(sh); times.append(t)
    return seq, times


def kag_shops(job):
    seed, opp = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    a = fidelity.make_agent(opp)
    b = fidelity.make_agent('pass:')
    g = engine.load_kagsim().Game(seed=seed)
    seq = []
    while not engine._val(g.done):
        o0, o1 = g.observe(0), g.observe(1)
        g.step(a(o0), b(o1))
        sh = (o0.get('town') or {}).get('unlocked_shops') or []
        if len(sh) > len(seq):
            seq = list(sh)
    return seed, opp.split('/')[-1], seq


def main():
    eps = [e for e in json.load(open(f'{LS}/episode_table.json')) if str(e.get('submission_id')) == '56156662']
    with ProcessPoolExecutor(max_workers=8) as pool:
        seqs = list(pool.map(seq_of, eps))
    print("解锁步（首局）:", seqs[0][1][:10])
    for k in range(1, 6):
        c = Counter(tuple(s[:k]) for s, _ in seqs)
        print(f"前 {k} 家商店：不同序列 {len(c)}，最大组 {c.most_common(1)[0][1]} 局，≥8 局的组覆盖 {sum(v for v in c.values() if v >= 8)}/{len(seqs)}")
    jobs = [(s, o) for s in (700001, 700098, 700195) for o in ('pass:', f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', f'sub:{M}/v2_survival_guard/main.py')]
    with ProcessPoolExecutor(max_workers=8) as pool:
        ks = list(pool.map(kag_shops, jobs))
    print("kagsim 同 seed 不同行为下的商店序列（前 5）:")
    for seed, opp, seq in ks:
        print(f"  seed {seed} 0号位={opp:20s} {seq[:5]}")


if __name__ == '__main__':
    main()
