"""其他五队唯一轨迹对 V120 粗筛（8 场景×双席位），top-15 再做全量 64×2。"""
import json, os, gzip, hashlib, sys, tempfile, pathlib, random, time
HERE = pathlib.Path(__file__).resolve().parent
HARNESS = HERE.parent / "v4_demand_race" / "harness"; sys.path.insert(0, str(HARNESS))
import arena
W = HERE.parent
V120 = str(W / "v120_hierarchical_top5_distillation" / "main.py")
SCEN = json.load(open(HARNESS / "scenarios_64.json"))
LOG = HERE / "lib" / "screen_teams.log"

def fullhash(acts): return hashlib.sha1("|".join(json.dumps(a, sort_keys=True) for a in acts[:719]).encode()).hexdigest()[:8]

def evaluate(team, ep, scen):
    ov = {"team": team, "prefer_ep": str(ep), "pin": 1}
    pf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(ov, pf); pf.close()
    os.environ["V5_PARAMS"] = pf.name; os.environ["V5_TEAM"] = team
    rep = arena.run(str(HERE / "main.py"), {"v120": V120}, [], scenarios=scen, workers=10, out=None)["v120"]
    os.unlink(pf.name)
    return rep

def main():
    rng = random.Random(7)
    screen_scen = rng.sample(SCEN, 8)
    results = []
    for team in ["tetsuya", "Crop_Dusta", "Driz_Lo", "yukino", "MtN"]:
        games = json.load(gzip.open(HERE / "lib" / f"{team}.json.gz", "rt"))["games"]
        uniq = {}
        for g in games:
            uniq.setdefault(fullhash(g["actions"]), g)
        eps = [str(g["ep"]) for g in uniq.values()]
        rng.shuffle(eps); eps = eps[:120]
        t0 = time.time()
        for i, ep in enumerate(eps):
            rep = evaluate(team, ep, screen_scen)
            r = {"team": team, "ep": ep, "W": rep["W"], "L": rep["L"], "wr": rep["winrate"], "margin": rep["mean_margin"], "phase": "screen"}
            results.append(r)
            with open(LOG, "a") as fh: fh.write(json.dumps(r) + "\n")
            if (i + 1) % 20 == 0:
                print(f"{team}: {i+1}/{len(eps)} ({time.time()-t0:.0f}s)", flush=True)
    top = sorted(results, key=lambda r: (-r["wr"], -r["margin"]))[:15]
    print("SCREEN_TOP15:", json.dumps(top), flush=True)
    for r in top:
        rep = evaluate(r["team"], r["ep"], SCEN)
        line = {"team": r["team"], "ep": r["ep"], "W": rep["W"], "L": rep["L"], "wr": rep["winrate"], "margin": rep["mean_margin"], "phase": "full"}
        with open(LOG, "a") as fh: fh.write(json.dumps(line) + "\n")
        print("FULL:", json.dumps(line), flush=True)
    print("SCREEN_DONE", flush=True)

if __name__ == "__main__":
    main()
