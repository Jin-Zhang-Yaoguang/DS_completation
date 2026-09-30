"""解剖满产出带的卖出模板：逐品的卖出时刻、批量、与库存/tick 的关系。"""
import json, sys, collections
d = json.load(open(sys.argv[1])); acts = d["actions"]
sells = collections.defaultdict(list)   # item -> [(t, qty)]
for t, a in enumerate(acts):
    for o in a.get("market") or []:
        if o and o[0] == "SELL" and len(o) >= 3:
            sells[o[1]].append((t, int(o[2])))
print(f"tape={d.get('team')} ep={d.get('ep')}")
for item in ("STRAWBERRY", "MILK", "WOOL", "MELON", "WHEAT", "FERTILIZER"):
    ss = sells.get(item, [])
    if not ss: continue
    qs = [q for _, q in ss]
    gaps = [ss[i+1][0]-ss[i][0] for i in range(len(ss)-1)]
    hours = collections.Counter(t % 24 for t, _ in ss)
    ticks = sum(q for t, q in ss if t % 4 == 0)
    first = ss[0][0]; last = ss[-1][0]
    print(f"{item:11s} n={len(ss):3d} qty={sum(qs):4d} batch(med/max)={sorted(qs)[len(qs)//2]}/{max(qs)} "
          f"first=d{first//24} last=d{last//24} gap(med)={sorted(gaps)[len(gaps)//2] if gaps else '-'}h tick%={ticks/max(1,sum(qs)):.0%}")
    byday = collections.Counter(t//24 for t, q in ss)
    qbyday = collections.defaultdict(int)
    for t, q in ss: qbyday[t//24] += q
    print("            qty/day:", {dd: qbyday[dd] for dd in sorted(qbyday)})
