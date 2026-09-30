"""跨局路径重复度测量：本地 agent 多局两两逐步动作重合率。

口径与 v71 determinism 一致：每步把 [farmer]+hands 动作序列化，两局同步比较，
重合率 = 相同步数 / 总步数。另报告首次分叉步。

用法: python3 path_overlap.py <agent.py 或 sub:/tape: spec> [--seeds 8] [--opp <spec>]
默认: 8 个 seed × 同一对手(ult 带)，两两重合；再加同 seed 不同对手的对照。
"""
import argparse
import importlib.util
import itertools
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
import engine  # noqa: E402
import fidelity  # noqa: E402

POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"


def make_agent(spec):
    if spec.endswith(".py") and ":" not in spec:
        p = Path(spec)
        m = importlib.util.module_from_spec(importlib.util.spec_from_file_location(f"a_{id(object())}", p))
        m.__spec__.loader.exec_module(m)
        return m.agent
    return fidelity.make_agent(spec)


def record_game(spec, opp_spec, seed):
    me = make_agent(spec)
    opp = make_agent(opp_spec)
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    trace = []
    fb = {"farmer": ["PASS"], "hands": [], "market": []}
    while not (g.done() if callable(g.done) else g.done):
        o0, o1 = g.observe(0), g.observe(1)
        try:
            a0 = me(o0)
        except Exception:
            a0 = dict(fb)
        try:
            a1 = opp(o1)
        except Exception:
            a1 = dict(fb)
        trace.append(json.dumps([a0.get("farmer") or []] + list(a0.get("hands") or [])))
        g.step(a0, a1)
    return trace, float(g.reward(0))


def overlap(t1, t2):
    n = min(len(t1), len(t2))
    same = sum(1 for a, b in zip(t1[:n], t2[:n]) if a == b)
    fork = next((i for i in range(n) if t1[i] != t2[i]), n)
    return same / max(1, n), fork


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--opp", default=f"tape:{POOL}/tapes/ult_normal.json")
    args = ap.parse_args()
    seeds = [1009 + 37 * i for i in range(args.seeds)]

    traces = {}
    for s in seeds:
        traces[s], bank = record_game(args.spec, args.opp, s)
        print(f"  seed {s}: bank {bank:.0f}", flush=True)
    ovs, forks = [], []
    for a, b in itertools.combinations(seeds, 2):
        ov, fk = overlap(traces[a], traces[b])
        ovs.append(ov)
        forks.append(fk)
    print(f"\n[不同 seed × 同对手] {len(ovs)} 对:")
    print(f"  重合率 中位 {statistics.median(ovs):.3f} 均值 {statistics.mean(ovs):.3f} "
          f"范围 {min(ovs):.3f}-{max(ovs):.3f}")
    print(f"  首分叉步 中位 {statistics.median(forks):.0f}")

    # 同 seed × 不同对手（对手条件敏感度）
    opps = [f"tape:{POOL}/tapes/ult_normal.json", f"sub:{POOL}/packs/y67_main.py",
            f"sub:{POOL}/packs/p955_main.py"]
    ovs2 = []
    for s in seeds[:3]:
        ts = [record_game(args.spec, o, s)[0] for o in opps]
        for t1, t2 in itertools.combinations(ts, 2):
            ov, _ = overlap(t1, t2)
            ovs2.append(ov)
    print(f"\n[同 seed × 不同对手] {len(ovs2)} 对: 重合率 中位 {statistics.median(ovs2):.3f} "
          f"范围 {min(ovs2):.3f}-{max(ovs2):.3f}")


if __name__ == "__main__":
    main()
