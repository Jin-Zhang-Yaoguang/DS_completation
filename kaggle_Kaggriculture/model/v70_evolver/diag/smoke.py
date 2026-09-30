"""冒烟:基线 cfg 在当前骨架上 8 局的 margin 必须与参考**逐分相同**(patch 须可退化为旧行为)。
用法: python diag/smoke.py --record   # 记录参考(改骨架前)
      python diag/smoke.py            # 校验(改骨架后),相同 exit 0,否则 exit 1
"""
import sys, json, argparse
from pathlib import Path
V = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V))
import arena, evolve, space

REF = V / "runs" / "_funsearch" / "smoke_ref.json"


def jobs_for(cfg):
    pool = evolve.load_seed_pool()
    seeds = evolve.pick_valid_seeds(pool)[:2]
    opps = arena.default_opponents()[:4]
    return [(cfg, op, sd) for sd in seeds for op in opps]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--cfg", default=str(V / "runs" / "_funsearch" / "baseline.json"))
    a = ap.parse_args()
    d = json.loads(Path(a.cfg).read_text())
    cfg = space.clamp(d.get("cfg", d))
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(14) as ex:
        ms = list(ex.map(arena.play_one, jobs_for(cfg)))
    if a.record:
        REF.write_text(json.dumps({"cfg": cfg, "margins": ms}))
        print("recorded", [round(x) for x in ms])
        return 0
    ref = json.loads(REF.read_text())["margins"]
    same = all(abs(x - y) < 1e-6 for x, y in zip(ms, ref))
    print("ref:", [round(x) for x in ref])
    print("now:", [round(x) for x in ms])
    print("SMOKE", "PASS" if same else "FAIL")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
