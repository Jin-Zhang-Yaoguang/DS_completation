"""最优响应制表：主家族内每条唯一续盘 × 64 场景 × 双席位 vs V120。
产出 lib/br_table.json：{ep: {"seed|seat": margin}}，并打印 oracle 上限。"""
import json, os, gzip, hashlib, sys, tempfile, pathlib, collections, time
HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent / "v4_demand_race" / "harness"
sys.path.insert(0, str(HARNESS))
import arena
W = HERE.parent
V120 = str(W / "v120_hierarchical_top5_distillation" / "main.py")
SCEN = json.load(open(HARNESS / "scenarios_64.json"))
OUT = HERE / "lib" / "br_table.json"

def fullhash(acts):
    return hashlib.sha1("|".join(json.dumps(a, sort_keys=True) for a in acts[:719]).encode()).hexdigest()[:8]

def main():
    games = json.load(gzip.open(HERE / "lib" / "OceanMix.json.gz", "rt"))["games"] + \
            json.load(gzip.open(HERE / "lib" / "V120tape.json.gz", "rt"))["games"]
    def ph(acts, n): return hashlib.sha1("|".join(json.dumps(a, sort_keys=True) for a in acts[:n]).encode()).hexdigest()[:8]
    fam = collections.Counter(ph(g["actions"], 72) for g in games)
    main_fam = fam.most_common(1)[0][0]
    uniq = {}
    for g in games:
        if ph(g["actions"], 72) != main_fam:
            continue
        h = fullhash(g["actions"])
        uniq.setdefault(h, g)
    print(f"主家族 {sum(fam.values())} 场中 {len(uniq)} 条唯一 tape", flush=True)
    table = json.load(open(OUT)) if OUT.exists() else {}
    t0 = time.time()
    for i, (h, g) in enumerate(uniq.items()):
        ep = str(g["ep"])
        if ep in table:
            continue
        ov = {"team": "OceanMix+V120tape", "prefer_ep": ep, "pin": 1}
        pf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(ov, pf); pf.close()
        os.environ["V5_PARAMS"] = pf.name; os.environ["V5_TEAM"] = ov["team"]
        rep = arena.run(str(HERE / "main.py"), {"v120": V120}, [], scenarios=SCEN, workers=10, out=None)["v120"]
        os.unlink(pf.name)
        table[ep] = {f"{r['seed']}|{r['seat']}": r["margin"] for r in rep["rows"]}
        json.dump(table, open(OUT, "w"))
        print(f"[{i+1}/{len(uniq)}] ep={ep} hash={h} W={rep['W']} L={rep['L']} wr={rep['winrate']:.3f} margin={rep['mean_margin']:+.0f}  ({time.time()-t0:.0f}s)", flush=True)
    # oracle
    keys = sorted(next(iter(table.values())).keys())
    oracle_w = sum(1 for k in keys if max(table[ep][k] for ep in table) > 0)
    print(f"ORACLE（每场景每席位取最优 tape）: {oracle_w}/{len(keys)} = {oracle_w/len(keys):.1%}")
    # 按 seed 配对（同一 tape 两席位）oracle
    seeds = sorted({k.split('|')[0] for k in keys})
    pair_w = 0
    for s in seeds:
        best = max(table[ep].get(f"{s}|0", -1e9) + table[ep].get(f"{s}|1", -1e9) for ep in table)
        pair_w += best > 0
    print(f"ORACLE（每 seed 选一条 tape，双席位 margin 和>0）: {pair_w}/{len(seeds)}")
    print("TABULATE_DONE", flush=True)


if __name__ == "__main__":
    main()