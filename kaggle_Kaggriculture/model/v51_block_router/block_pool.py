"""B 阶段块池扫描:对带库所有带,在每个 6 天块边界尝试接到 fam_F 骨架上,
单人产出验证 → 合格 (边界, 尾部) 接入点清单。
用法: python block_pool.py [extra_tape_dir]
"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
GRAFT_DIR = HERE / "grafts"
GRAFT_DIR.mkdir(exist_ok=True)

CUTS = [72, 144, 288, 432, 576]
SEEDS = (11, 22, 33)
# 我方基准(fam_F 骨架本尊)各 seed 产出;接入点合格线 = 不低于 max(基准, tail 本尊) - 1500
F = json.load(open(TAPES / "fam_F_new.json"))["actions"]


def one(job):
    import fidelity
    kind, name, cut, seed, path = job
    r = fidelity.play(f"tape:{path}", "pass:", seed, [])
    return kind, name, cut, seed, int(r["bank"][0])


if __name__ == "__main__":
    dirs = [TAPES] + ([Path(sys.argv[1])] if len(sys.argv) > 1 else [])
    tails = {}
    for d in dirs:
        for f in sorted(d.glob("*.json")):
            if f.stem == "fam_F_new":
                continue
            try:
                acts = json.load(open(f))["actions"]
                if len(acts) >= 719:
                    tails[f.stem] = acts
            except Exception:
                pass
    print(f"{len(tails)} tails × {len(CUTS)} cuts")

    jobs = []
    for name, acts in tails.items():
        jobs.append(("pure", name, 0, 11, TAPES / f"{name}.json" if (TAPES / f"{name}.json").exists() else None))
    # pure 本尊只跑 seed11 做参照(路径可能在 extra dir)
    jobs = []
    for d in dirs:
        for name in tails:
            p = d / f"{name}.json"
            if p.exists():
                for sd in SEEDS:
                    jobs.append(("pure", name, 0, sd, p))
                break
    for name, acts in tails.items():
        for cut in CUTS:
            gp = GRAFT_DIR / f"g_{name}_{cut}.json"
            if not gp.exists():
                json.dump({"actions": F[:cut] + acts[cut:]}, gp.open("w"))
            for sd in SEEDS:
                jobs.append(("graft", name, cut, sd, gp))
    # fam_F 基准
    for sd in SEEDS:
        jobs.append(("base", "fam_F_new", 0, sd, TAPES / "fam_F_new.json"))

    print(f"{len(jobs)} runs ...", flush=True)
    res = {}
    done = 0
    with ProcessPoolExecutor(8) as ex:
        for kind, name, cut, sd, bank in ex.map(one, jobs, chunksize=4):
            res[(kind, name, cut, sd)] = bank
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)

    base = [res[("base", "fam_F_new", 0, sd)] for sd in SEEDS]
    print("fam_F base:", base)
    out = []
    for name in sorted(tails):
        pure = [res.get(("pure", name, 0, sd)) for sd in SEEDS]
        row = {"tail": name, "pure": pure, "cuts": {}}
        for cut in CUTS:
            g = [res.get(("graft", name, cut, sd)) for sd in SEEDS]
            if None in g:
                continue
            ref = [max(b, p) if p else b for b, p in zip(base, pure)] if None not in pure else base
            ok = all(gv >= rv - 1500 for gv, rv in zip(g, ref))
            row["cuts"][cut] = {"banks": g, "ok": ok}
        out.append(row)
        oks = [str(c) for c in CUTS if row["cuts"].get(c, {}).get("ok")]
        print(f"{name:28s} pure={pure} OK@{','.join(oks) if oks else '-'}")
    json.dump(out, (HERE / "block_pool.json").open("w"), indent=1)
    print("saved block_pool.json")
