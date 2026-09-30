import json, collections, itertools
from pathlib import Path
HERE = Path(__file__).resolve().parent
R = json.load(open(HERE / "distill_raw.json"))
byc = collections.defaultdict(list)
for r in R: byc["|".join(r["shops"])].append(r)
def events(r):
    ev = [(int(t), "HIRE", c) for t, c in r["hires"].items()]
    ev += [(x[0], "BUY", tuple(x[1:])) for x in r["buys"]]
    ev += [(x[0], "FIELD", tuple(x[1:])) for x in r["field"]]
    return sorted(ev, key=lambda e: (e[0], e[1], str(e[2])))
for c, v in byc.items():
    if len(v) < 2: continue
    a, b = events(v[0]), events(v[1])
    k = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), None)
    print(f"\n### {c}  seed {v[0]['seed']} vs {v[1]['seed']}  银行 {v[0]['bank']:.0f} / {v[1]['bank']:.0f}")
    if k is None: print("  完全一致"); continue
    print(f"  首个不同事件 #{k}: A={a[k]}  B={b[k]}")
    sa = collections.Counter((e[1], e[2][0] if e[1] != "HIRE" else "HIRE") for e in a if e[0] >= a[k][0])
    sb = collections.Counter((e[1], e[2][0] if e[1] != "HIRE" else "HIRE") for e in b if e[0] >= b[k][0])
    print("  分叉后事件数差(A-B):", {kk: sa[kk] - sb[kk] for kk in set(sa) | set(sb) if sa[kk] != sb[kk]})
    ta = [e for e in a if a[k][0] <= e[0] < a[k][0] + 30][:8]; tb = [e for e in b if b[k][0] <= e[0] < b[k][0] + 30][:8]
    print("  A 分叉附近:", ta); print("  B 分叉附近:", tb)
