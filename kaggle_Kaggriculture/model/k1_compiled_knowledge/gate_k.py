"""K 系上线双门控（用户 2026-09-13 基准）：

  门控 1 表现：候选 vs 现有最强四模型（默认 y68f/y68c/y67/y66），
             每对 N seed × 双席位，报胜率与平均 margin。
  门控 2 自适应：跨局路径重合中位 < 0.1（防破译，参考 Majkel）。

用法: /opt/anaconda3/bin/python3 gate_k.py <候选 main.py> [--seeds 8]
两门全过才打印 PASS；任何产物仍须用户放行后才提交。
"""
import argparse
import importlib.util
import itertools
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"
# 滚动四强（E 类刷新，2026-09-14：y68g 2771 上线为新王）
_MOSAIC = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"
TOP4 = [
    ("y68g", f"{_MOSAIC}/y68g_main.py"),
    ("y68c", f"{POOL}/packs/y68c_main.py"),
    ("y68f", f"{POOL}/packs/y68f_main.py"),
    ("y67", f"{POOL}/packs/y67_main.py"),
]
OVERLAP_THRESHOLD = 0.1


def play_one(job):
    cand_path, opp_path, seed, seat, record = job
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity

    def load(p):
        spec = importlib.util.spec_from_file_location(f"m_{seed}_{seat}_{abs(hash(p))}", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        ns = vars(m)
        return ns.get("_ENTRY") or ns["agent"]

    me = load(cand_path)
    opp = fidelity.make_agent(f"sub:{opp_path}") if opp_path else \
        (lambda o: {"farmer": ["PASS"], "hands": [], "market": []})
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    agents = [None, None]
    agents[seat] = me
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
        if record:
            a = acts[seat]
            trace.append(json.dumps([a.get("farmer") or []] + list(a.get("hands") or [])))
        g.step(acts[0], acts[1])
    mine, theirs = float(g.reward(seat)), float(g.reward(1 - seat))
    return mine, theirs, trace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate")
    ap.add_argument("--seeds", type=int, default=8)
    args = ap.parse_args()
    cand = str(Path(args.candidate).resolve())
    seeds = [1009 + 37 * i for i in range(args.seeds)]

    # ---- 门控 1：四强对局 ----
    jobs = [(cand, opp, s, seat, False) for _, opp in TOP4 for s in seeds for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(play_one, jobs))
    print("== 门控 1（表现：vs 最强四模型）==")
    i = 0
    total_w = total_n = 0
    for name, _ in TOP4:
        wins = 0
        margins = []
        for s in seeds:
            for seat in (0, 1):
                mine, theirs, _ = res[i]
                i += 1
                wins += 1 if mine > theirs else 0
                margins.append(mine - theirs)
        n = len(seeds) * 2
        total_w += wins
        total_n += n
        print(f"  vs {name}: 胜率 {wins}/{n}  margin 均值 {statistics.mean(margins):+.0f} "
              f"中位 {statistics.median(margins):+.0f}")
    wr = total_w / total_n
    print(f"  合计胜率 {total_w}/{total_n} = {wr:.1%}")

    # ---- 门控 2：自适应（重合中位 < 0.1）----
    jobs2 = [(cand, TOP4[2][1], s, 0, True) for s in seeds[:6]]
    with ProcessPoolExecutor(max_workers=6) as pool:
        res2 = list(pool.map(play_one, jobs2))
    traces = [t for _, _, t in res2]
    ovs = []
    for a, b in itertools.combinations(range(len(traces)), 2):
        t1, t2 = traces[a], traces[b]
        n2 = min(len(t1), len(t2))
        ovs.append(sum(1 for x, y in zip(t1[:n2], t2[:n2]) if x == y) / max(1, n2))
    med = statistics.median(ovs)
    print(f"\n== 门控 2（自适应：跨局重合中位 < {OVERLAP_THRESHOLD}）==")
    print(f"  重合中位 {med:.3f}  范围 {min(ovs):.3f}-{max(ovs):.3f}")

    g1 = wr >= 0.5
    g2 = med < OVERLAP_THRESHOLD
    print(f"\n门控 1 {'PASS' if g1 else 'FAIL'}（胜率 {wr:.1%}，线 50%）  "
          f"门控 2 {'PASS' if g2 else 'FAIL'}（{med:.3f}，线 {OVERLAP_THRESHOLD}）")
    print("总判定:", "PASS —— 交用户放行" if g1 and g2 else "FAIL")


if __name__ == "__main__":
    main()
