"""M1:任务结构统计——动作是否消耗/产生背包物品、背包上限、取货→使用链长度、每天事件与移动基准。"""
import json, gzip, glob, collections, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
inv_eff = collections.defaultdict(collections.Counter)   # op -> Counter(("+item"/"-item"/"0"))
cap = 0; chain_gap = []; chain_between = []; ops_day = collections.Counter(); moves = 0; passes = 0; works = 0
daily = []
for fn in sorted(glob.glob(str(HERE / "data" / "tape_*.json.gz"))):
    D = json.load(gzip.open(fn, "rt")); S = D["steps"]
    for t in range(len(S) - 1):
        a, b = S[t], S[t + 1]
        for i, c in enumerate(a["cmds"][:len(a["units"])]):
            op = c[0] if c else "PASS"
            if op in MOVES: moves += 1; continue
            if op == "PASS": passes += 1; continue
            works += 1; ops_day[op] += 1
            if t % 24 == 23: continue
            i0 = a["inv"][i] if i < len(a["inv"]) else {}; i1 = b["inv"][i] if i < len(b["inv"]) else {}
            d = {k: i1.get(k, 0) - i0.get(k, 0) for k in set(i0) | set(i1) if i1.get(k, 0) != i0.get(k, 0)}
            key = ",".join(f"{'+' if v > 0 else '-'}{k}" for k, v in sorted(d.items())) or "0"
            inv_eff[op][key] += 1
            cap = max(cap, sum(i1.values()))
    # 链:单位 PICKUP 后,到背包清空之间的步数与中间工作数
    for day in range(30):
        for i in range(12):
            carrying = None; start = None; between = 0
            for t in range(day * 24 + 1, day * 24 + 23):
                if t + 1 >= len(S) or i >= len(S[t]["units"]): break
                c = S[t]["cmds"][i] if i < len(S[t]["cmds"]) else ["PASS"]
                op = c[0] if c else "PASS"
                inv = sum((S[t + 1]["inv"][i] if i < len(S[t + 1]["inv"]) else {}).values())
                if op == "PICKUP" and start is None: start = t; between = 0
                elif start is not None and op not in MOVES and op != "PASS": between += 1
                if start is not None and inv == 0 and t > start:
                    chain_gap.append(t - start); chain_between.append(between); start = None
    for day in range(30):
        w = sum(1 for t in range(day*24, min(day*24+24, len(S))) for i, c in enumerate(S[t]["cmds"][:len(S[t]["units"])]) if c and c[0] not in MOVES and c[0] != "PASS")
        mv = sum(1 for t in range(day*24, min(day*24+24, len(S))) for i, c in enumerate(S[t]["cmds"][:len(S[t]["units"])]) if c and c[0] in MOVES)
        us = sum(len(S[t]["units"]) for t in range(day*24, min(day*24+24, len(S))))
        daily.append((day, w, mv, us))
print(f"12 局合计: 工作 {works} 移动 {moves} PASS {passes};工作动作分布 {ops_day.most_common()}")
print("动作对该单位背包的影响(非日终步):")
for op, cnt in inv_eff.items(): print(f"  {op:20s} {cnt.most_common(6)}")
print(f"单人背包最多件数 {cap}")
print(f"取货链:从 PICKUP 到背包清空 步数中位 {st.median(chain_gap)} 90分位 {sorted(chain_gap)[int(len(chain_gap)*0.9)]};链内其他工作数中位 {st.median(chain_between)} 最大 {max(chain_between)};链数 {len(chain_gap)}")
byday = collections.defaultdict(list)
for d, w, mv, us in daily: byday[d].append((w, mv, us))
print("每天(12 局中位) 工作/移动/单位步:", " ".join(f"d{d}:{st.median(x[0] for x in v):.0f}/{st.median(x[1] for x in v):.0f}/{st.median(x[2] for x in v):.0f}" for d, v in sorted(byday.items()) if d % 3 == 0))
