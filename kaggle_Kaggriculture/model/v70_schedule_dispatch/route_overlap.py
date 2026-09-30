import json, collections, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
D = json.load(open(HERE / "schedule_routes_raw.json"))
def evs(d, cat):
    if cat == "雇工": return [(int(t), "HIRE") for t, c in d["hires"].items() for _ in range(c) if int(t) >= 144]
    if cat == "买单": return [(x[0], tuple(x[1:])) for x in d["buys"] if x[0] >= 144]
    return [(x[0], tuple(x[1:])) for x in d["field"] if x[0] >= 144]
def match(a, b, tol=3):
    used = [False] * len(b); hit = 0
    idx = collections.defaultdict(list)
    for j, (t, k) in enumerate(b): idx[k].append((t, j))
    for t, k in a:
        for tb, j in idx[k]:
            if not used[j] and abs(tb - t) <= tol: used[j] = True; hit += 1; break
    return hit / max(1, max(len(a), len(b))), len(a), len(b)
res = collections.defaultdict(list); worst = []
for rid, v in D.items():
    a, b = v["3001"], v["3002"]
    row = []
    for cat in ("雇工", "买单", "布局"):
        r, na, nb = match(evs(a, cat), evs(b, cat)); res[cat].append(r); row.append((cat, round(r, 3), na, nb))
    worst.append((min(x[1] for x in row), rid, row, round(a["bank"]), round(b["bank"])))
for cat, v in res.items(): print(f"{cat}: 两 seed 事件重合率(±3 步) 中位 {st.median(v):.1%} 最低 {min(v):.1%} ≥95% 的路线 {sum(x>=0.95 for x in v)}/{len(v)}")
print("重合最低的 5 条路线:")
for w in sorted(worst)[:5]: print("  ", w)
