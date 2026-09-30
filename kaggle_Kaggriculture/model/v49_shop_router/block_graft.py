"""B 阶段可行性:三带在各 6 天块边界(144/288/432/576)互换尾部的单人产出矩阵。
判定块级拼接是否普遍成立(成立 → 块路由架构可建)。"""
import sys, json, itertools
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"

NAMES = {"F": "fam_F_new", "R": "rb_7925cb146f", "C": "cand_0_ec979a"}
ACTS = {k: json.load(open(TAPES / f"{v}.json"))["actions"] for k, v in NAMES.items()}
CUTS = [144, 288, 432, 576]
SEEDS = (11, 22, 33)


def one(job):
    import fidelity
    head, tail, cut, seed = job
    if head == tail:
        spec = f"tape:{TAPES}/{NAMES[head]}.json"
        r = fidelity.play(spec, "pass:", seed, [])
        return (head, tail, cut, seed, int(r["bank"][0]))
    p = HERE / f"_bg_{head}{tail}_{cut}.json"
    r = fidelity.play(f"tape:{p}", "pass:", seed, [])
    return (head, tail, cut, seed, int(r["bank"][0]))


if __name__ == "__main__":
    for h, t in itertools.product("FRC", repeat=2):
        if h == t:
            continue
        for c in CUTS:
            p = HERE / f"_bg_{h}{t}_{c}.json"
            json.dump({"actions": ACTS[h][:c] + ACTS[t][c:]}, p.open("w"))
    jobs = []
    for h, t in itertools.product("FRC", repeat=2):
        if h == t:
            jobs += [(h, t, 0, sd) for sd in SEEDS]
        else:
            jobs += [(h, t, c, sd) for c in CUTS for sd in SEEDS]
    res = {}
    with ProcessPoolExecutor(8) as ex:
        for h, t, c, sd, bank in ex.map(one, jobs, chunksize=2):
            res.setdefault((h, t, c), []).append(bank)
    base = {k: res[(k, k, 0)] for k in "FRC"}
    for k in "FRC":
        print(f"pure {k} ({NAMES[k]}): {base[k]}")
    print(f"\n{'head':4s} {'tail':4s} {'cut':5s} banks (vs tail 本尊差值)")
    for h, t in itertools.product("FRC", repeat=2):
        if h == t:
            continue
        for c in CUTS:
            banks = res[(h, t, c)]
            diffs = [b - tb for b, tb in zip(banks, base[t])]
            ok = all(abs(d) < 1500 for d in diffs)
            print(f"{h:4s} {t:4s} {c:<5d} {banks}  diff={diffs}  {'OK' if ok else 'LOSSY'}")
