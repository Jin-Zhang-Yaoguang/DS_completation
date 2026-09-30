"""v58 马赛克:t955 主 schedule 为骨架,私有同族带的天段(24 步)替换,贪心逐天。
快筛=单人产出(不掉>1200);复筛=门控面板 4 局(v56/v54c 各 2)margin 不降。
用法: python mosaic.py <tape_idx> <day_from> <day_to>
"""
import sys, json, hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
NEWPOOL = HERE.parent / "v51_block_router" / "newpool"
SCRATCH = Path("/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad")

def wover(a, b, n=144):
    sa = [json.dumps({"f": x.get("farmer"), "h": x.get("hands")}, sort_keys=True) for x in a[:n]]
    sb = [json.dumps({"f": x.get("farmer"), "h": x.get("hands")}, sort_keys=True) for x in b[:n]]
    return sum(x == y for x, y in zip(sa, sb)) / n

def load_family(base_acts):
    fam = []
    for f in sorted(NEWPOOL.glob("op_*.json")):
        d = json.load(open(f))
        if wover(base_acts, d["actions"]) >= 0.90:
            fam.append((f.stem, d["actions"], d.get("bank", 0)))
    for name in ("gold_chocolat_e3bb880a", "rb_84a8a63442", "rb_fed85a15a6", "fam_F_new", "rb_7925cb146f", "cand_0_ec979a"):
        p = TAPES / name
        p = TAPES / f"{name}.json"
        if p.exists():
            acts = json.load(open(p))["actions"]
            if wover(base_acts, acts) >= 0.90:
                fam.append((name, acts, 0))
    return fam

def solo_bank(path, sd):
    import fidelity
    return fidelity.play(f"tape:{path}", "pass:", sd, [])["bank"][0]

def gate_margin(path, sd_seat_opp):
    import fidelity
    sd, seat, opp = sd_seat_opp
    specs = [None, None]
    specs[seat] = f"tape:{path}"
    specs[1 - seat] = f"sub:{opp}"
    r = fidelity.play(specs[0], specs[1], sd, [])
    return r["bank"][seat] - r["bank"][1 - seat]

if __name__ == "__main__":
    ti = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    d_from = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    d_to = int(sys.argv[3]) if len(sys.argv) > 3 else 29
    base = json.load(open(TAPES / f"pub_t955_{ti}.json"))["actions"]
    fam = load_family(base)
    print(f"tape{ti}: 同族段库 {len(fam)} 条", flush=True)
    GOPPS = [str(SCRATCH / "v56_main.py"), str(HERE.parent / "v51_block_router" / "dist_v54c" / "main.py")]
    cur = [json.loads(json.dumps(a)) for a in base]
    cur_p = HERE / f"mosaic_t{ti}.json"
    json.dump({"actions": cur}, cur_p.open("w"))
    with ProcessPoolExecutor(8) as ex:
        base_solo = list(ex.map(solo_bank, [cur_p]*3, (11, 22, 33)))
        gjobs = [(sd, seat, o) for sd in (300,) for seat in (0, 1) for o in GOPPS]
        base_gate = sum(ex.map(gate_margin, [cur_p]*len(gjobs), gjobs)) / len(gjobs)
        print(f"base solo={[int(x) for x in base_solo]} gate_margin={base_gate:+.0f}", flush=True)
        n_swap = 0
        for day in range(d_from, d_to + 1):
            s0, s1 = day * 24, day * 24 + 24
            best = None
            for name, acts, _ in fam:
                trial = cur[:s0] + [json.loads(json.dumps(a)) for a in acts[s0:s1]] + cur[s1:]
                if json.dumps(trial[s0:s1], sort_keys=True) == json.dumps(cur[s0:s1], sort_keys=True):
                    continue
                tp = HERE / f"_trial_t{ti}.json"
                json.dump({"actions": trial}, tp.open("w"))
                solos = list(ex.map(solo_bank, [tp]*3, (11, 22, 33)))
                if any(solos[i] < base_solo[i] - 1200 for i in range(3)):
                    continue
                g = sum(ex.map(gate_margin, [tp]*len(gjobs), gjobs)) / len(gjobs)
                if g > (best[0] if best else base_gate - 300):
                    best = (g, name, trial, solos)
            if best and best[0] >= base_gate - 300:
                g, name, trial, solos = best
                cur = trial
                n_swap += 1
                json.dump({"actions": cur}, cur_p.open("w"))
                print(f"day{day}: SWAP<-{name[:20]} gate {g:+.0f} solo {[int(x) for x in solos]}", flush=True)
            else:
                print(f"day{day}: keep", flush=True)
    print(f"done: {n_swap} 天段替换 -> {cur_p}", flush=True)
