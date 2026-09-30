"""K1 vs y68 家族正式评估：每对手 16 场（8 seed×双席位），胜率+margin+轨迹重合。"""
import importlib.util
import itertools
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"
MOS = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"
FAMILY = [
    ("y68g", f"{MOS}/y68g_main.py"),
    ("y68c", f"{POOL}/packs/y68c_main.py"),
    ("y68f", f"{POOL}/packs/y68f_main.py"),
    ("y68a", f"{POOL}/packs/y68a_main.py"),
]
SEEDS = [1009 + 137 * i for i in range(8)]


def one(job):
    opp_path, seed, seat = job
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_{seed}_{seat}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)   # 完整配置：t0 池选择开
    opp = fidelity.make_agent(f"sub:{opp_path}")
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    agents = [None, None]
    agents[seat] = mod.agent
    agents[1 - seat] = opp
    trace = []
    fb = {"farmer": ["PASS"], "hands": [], "market": []}
    while not (g.done() if callable(g.done) else g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = []
        for i2 in (0, 1):
            try:
                acts.append(agents[i2](obs[i2]))
            except Exception:
                acts.append(dict(fb))
        a = acts[seat]
        trace.append(json.dumps([a.get("farmer") or []] + list(a.get("hands") or [])))
        g.step(acts[0], acts[1])
    return float(g.reward(seat)), float(g.reward(1 - seat)), trace


def overlap(t1, t2):
    n = min(len(t1), len(t2))
    return sum(1 for a, b in zip(t1[:n], t2[:n]) if a == b) / max(1, n)


def main():
    jobs = [(p, s, seat) for _, p in FAMILY for s in SEEDS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    all_traces = []
    i = 0
    total_w = total_n = 0
    print(f"{'对手':6s} | 胜率      | margin 均值/中位 | own 均值 | 组内重合中位")
    for name, _ in FAMILY:
        wins = 0
        margins, owns, traces = [], [], []
        for s in SEEDS:
            for seat in (0, 1):
                mine, theirs, tr = res[i]
                i += 1
                wins += 1 if mine > theirs else 0
                margins.append(mine - theirs)
                owns.append(mine)
                traces.append(tr)
        all_traces.extend(traces)
        ovs = [overlap(a, b) for a, b in itertools.combinations(traces, 2)]
        total_w += wins
        total_n += 16
        print(f"{name:6s} | {wins}/16      | {statistics.mean(margins):+9.0f}/{statistics.median(margins):+9.0f} "
              f"| {statistics.mean(owns):8.0f} | {statistics.median(ovs):.3f}")
    # 总体重合：拆分同 seed / 异 seed（线上每局 seed 都不同，异 seed 口径才是真实暴露面）
    import random
    rng = random.Random(7)
    meta = [(s, seat) for _ in FAMILY for s in SEEDS for seat in (0, 1)]
    same, diff = [], []
    for a, b in itertools.combinations(range(len(all_traces)), 2):
        (same if meta[a][0] == meta[b][0] else diff).append((a, b))
    diff_s = rng.sample(diff, min(400, len(diff)))
    ov_same = [overlap(all_traces[a], all_traces[b]) for a, b in same]
    ov_diff = [overlap(all_traces[a], all_traces[b]) for a, b in diff_s]
    print(f"同 seed 对({len(same)}): 中位 {statistics.median(ov_same):.3f} "
          f"≥0.9 占比 {sum(1 for x in ov_same if x >= 0.9)/len(ov_same):.1%}")
    print(f"异 seed 对(抽{len(diff_s)}): 中位 {statistics.median(ov_diff):.3f} "
          f"p90 {sorted(ov_diff)[int(len(ov_diff)*0.9)]:.3f} max {max(ov_diff):.3f}")
    ovs_all = ov_same + ov_diff
    print(f"\n合计胜率 {total_w}/{total_n} = {total_w/total_n:.1%}")
    print(f"总体轨迹重合(64 局抽样 300 对): 中位 {statistics.median(ovs_all):.3f} "
          f"均值 {statistics.mean(ovs_all):.3f} 范围 {min(ovs_all):.3f}-{max(ovs_all):.3f}")


if __name__ == "__main__":
    main()
