"""线上市场指纹分布:从 v41/rb7925 线上 replay 提取 (dw0,dw1,d28),按 v50 路由规则分类,
统计各分支触发率与我方实际胜率 → 预测/校准 v50 线上行为。"""
import json, collections
from pathlib import Path

ROOT = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data")
DIRS = ["v41/replays", "v41_56044730/replays", "rb7925_56044732/replays", "v50/replays"]
ME = "datatuu"


def classify(dw0, dw1, d28):
    if dw0 is None:
        return "?"
    if -30 <= dw0 <= -24 and 12 <= dw1 <= 20:
        return "F(13/8-clone)"
    if dw0 <= -31:
        return "rb(big-perturb)"
    if abs(dw0 + 14) <= 3 and abs(dw1 - 3) <= 3 and d28 <= -2:
        return "F(ocean-t28)"
    return "shop-table"


stats = collections.defaultdict(lambda: [0, 0.0])
seen = set()
n_files = 0
for d in DIRS:
    p = ROOT / d
    if not p.exists():
        continue
    for f in p.glob("episode-*-replay.json"):
        if f.name in seen:
            continue
        seen.add(f.name)
        try:
            rep = json.load(open(f))
        except Exception:
            continue
        info = rep.get("info") or {}
        names = info.get("TeamNames") or []
        steps = rep.get("steps") or []
        if len(steps) < 35:
            continue
        # 我方席位
        my_seat = None
        for i, nm in enumerate(names):
            if ME.lower() in str(nm).lower():
                my_seat = i
        if my_seat is None:
            continue
        # market inventory WHEAT 序列(从任一席位的 observation)
        inv = {}
        for t in range(0, 34):
            try:
                ob = steps[t][0].get("observation") or {}
                mkt = ob.get("market") or {}
                invd = mkt.get("inventory") or {}
                if "WHEAT" in invd:
                    inv[t] = invd["WHEAT"]
            except Exception:
                pass
        dw0 = inv.get(1, 0) - inv.get(0, 0) if 0 in inv and 1 in inv else None
        dw1 = inv.get(2, 0) - inv.get(1, 0) if 1 in inv and 2 in inv else None
        d28 = inv.get(29, 0) - inv.get(28, 0) if 28 in inv and 29 in inv else 0
        cls = classify(dw0, dw1 or 0, d28)
        # 胜负
        try:
            r0 = steps[-1][my_seat].get("reward")
            r1 = steps[-1][1 - my_seat].get("reward")
            win = 1.0 if r0 > r1 else (0.5 if r0 == r1 else 0.0)
        except Exception:
            continue
        stats[cls][0] += 1
        stats[cls][1] += win
        n_files += 1

print(f"分析 {n_files} 局线上对局")
tot = sum(v[0] for v in stats.values())
for cls, (n, w) in sorted(stats.items(), key=lambda x: -x[1][0]):
    print(f"  {cls:18s} {n:4d} 局 ({100*n/max(tot,1):.0f}%)  我方胜率 {w/max(n,1):.3f}")
