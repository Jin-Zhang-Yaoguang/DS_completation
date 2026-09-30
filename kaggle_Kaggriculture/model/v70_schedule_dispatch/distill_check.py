import json, collections, itertools
from pathlib import Path
HERE = Path(__file__).resolve().parent
R = json.load(open(HERE / "distill_raw.json"))
SEG = [("t0-143", 0, 144), ("t144-647", 144, 648), ("t648-719", 648, 720)]
def seq(r, cat, lo, hi, loose=False):
    if cat == "雇工":
        return tuple((int(t), c) for t, c in sorted(r["hires"].items(), key=lambda kv: int(kv[0])) if lo <= int(t) < hi)
    if cat == "买单":
        return tuple(tuple(x if not loose else x[:3]) for x in r["buys"] if lo <= x[0] < hi)
    if cat == "布局":
        return tuple(tuple(x) for x in r["field"] if lo <= x[0] < hi)
def report(label, key):
    print(f"\n== {label} ==")
    for cat in ("雇工", "买单", "布局"):
        row = []
        for name, lo, hi in SEG:
            seqs = [key(r, cat, lo, hi) for r in R]
            mode_n = collections.Counter(seqs).most_common(1)[0][1]
            byc = collections.defaultdict(list)
            for r, s in zip(R, seqs): byc["|".join(r["shops"])].append(s)
            pairs = [(a == b) for v in byc.values() for a, b in itertools.combinations(v, 2)]
            row.append(f"{name}: 同众数 {mode_n}/{len(R)} 同组合 {sum(pairs)}/{len(pairs)}")
        print(f"  {cat}: " + " | ".join(row))
report("精确一致(含步号与数量)", lambda r, c, lo, hi: seq(r, c, lo, hi))
# 忽略步号:只比内容顺序
def nostep(r, c, lo, hi):
    s = seq(r, c, lo, hi)
    if c == "雇工": return tuple(sum(x[1] for x in s if (x[0] // 24) == d) for d in range(lo // 24, (hi + 23) // 24))
    return tuple(x[1:] for x in s)
report("按天汇总雇工 / 忽略步号的买单与布局", nostep)
# 雇工日程与在场人数
days = range(30)
hday = [collections.Counter(sum(c for t, c in r["hires"].items() if int(t) // 24 == d) for r in R) for d in days]
print("\n每天雇工数(众数:局数):", " ".join(f"{h.most_common(1)[0][0]}:{h.most_common(1)[0][1]}" for h in hday))
land = collections.Counter(tuple(x[0] for x in r["buys"] if x[1] == "BUY_LAND") for r in R)
print("买地步号分布:", land.most_common(4))
animals = collections.Counter(tuple((x[0], x[2], x[3]) for x in r["buys"] if x[1] == "BUY_ANIMAL") for r in R)
print("买牲畜序列种类数:", len(animals), " 众数:", animals.most_common(1)[0][0][:12], "…", animals.most_common(1)[0][1], "局")
