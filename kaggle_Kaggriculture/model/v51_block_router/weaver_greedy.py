"""weaver v3:贪心逐对筛选改写。每对 = (PICKUP 插入点, 一串 FERTILIZE)。
任一 seed 相对当前基线掉 >300 金即回退该对。"""
import sys, json, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
import fidelity
from fert_weaver import replay_record, TAPES, PICK_QTY

def build_pairs(tape_name, seeds=(11,22,33)):
    recs, spots_l, opps_l = [], [], []
    for sd in seeds:
        rec, spots, opps = replay_record(tape_name, sd)
        recs.append(rec); spots_l.append(spots); opps_l.append(set(opps))
    shed_spots = set.intersection(*[set(s) for s in spots_l])
    opps = sorted(set.intersection(*opps_l))
    def all_pass_at(tb, ui):
        for rc in recs:
            if tb >= len(rc) or ui >= len(rc[tb]): return False
            _, p, op, _ = rc[tb][ui]
            if op != "PASS" or p not in shed_spots: return False
        return True
    pairs = []
    used = set()
    for (t, ui) in opps:
        ins = None
        for tb in range(t-1, max(-1, t-200), -1):
            if (tb, ui) in used: continue
            if all_pass_at(tb, ui):
                ins = tb; break
        if ins is None: continue
        used.add((ins, ui))
        pairs.append({"pick": (ins, ui), "fert": (t, ui)})
    return pairs

def apply(acts, pairs):
    na = [json.loads(json.dumps(a)) for a in acts]
    for pr in pairs:
        for (tt, ui), op in [(pr["pick"], ["PICKUP","FERTILIZER",PICK_QTY]), (pr["fert"], ["FERTILIZE"])]:
            a = na[tt]
            units = [a.get("farmer") or ["PASS"]] + [list(h) for h in (a.get("hands") or [])]
            units[ui] = list(op)
            a["farmer"] = units[0]; a["hands"] = units[1:]
    return na

def banks(acts, seeds=(11,22,33)):
    tmp = HERE / "_tmp_weave.json"
    json.dump({"actions": acts}, tmp.open("w"))
    return [int(fidelity.play(f"tape:{tmp}", "pass:", sd, [])["bank"][0]) for sd in seeds]

if __name__ == "__main__":
    tape = sys.argv[1]
    acts = json.load(open(TAPES/f"{tape}.json"))["actions"]
    pairs = build_pairs(tape)
    print(f"{tape}: {len(pairs)} 对候选改写")
    base = banks(acts)
    print("base:", base)
    kept = []
    cur = base
    for i, pr in enumerate(pairs):
        trial = apply(acts, kept + [pr])
        b = banks(trial)
        if all(b[j] >= cur[j] - 300 for j in range(3)) and sum(b) > sum(cur):
            kept.append(pr); cur = b
            print(f"  +pair{i} (fert@t{pr['fert'][0]}u{pr['fert'][1]}) -> {b} KEEP")
        else:
            print(f"  +pair{i} (fert@t{pr['fert'][0]}u{pr['fert'][1]}) -> {b} revert")
    final = apply(acts, kept)
    out = TAPES / f"{tape}_fw.json"
    json.dump({"actions": final, "weaver": {"pairs": len(kept)}}, out.open("w"))
    print(f"最终保留 {len(kept)} 对: {cur} vs base {base}, 总增 {sum(cur)-sum(base):+d}")
