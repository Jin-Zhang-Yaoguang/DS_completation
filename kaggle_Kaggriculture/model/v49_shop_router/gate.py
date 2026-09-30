"""holdout 门控:sub: 口径候选 vs 20 对手带,新 seed,双席位,记录首店。
用法: python gate.py <out.jsonl> <name=path,name=path,...> <seed0> <n>
"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"

OPPS = ["fam_A_0w8l", "fam_B_cornhub", "fam_C_0w5l", "fam_D_0w5l", "fam_E_0w3l",
        "fam_F_new", "fam_G_new", "pert_0_b79742", "pert_1_22ebcc", "pert_2_0f8469",
        "pert_3_597210", "cand_0_ec979a", "cand_1_bf2b55", "cand_2_c333c1",
        "top_keiz_82acad", "top_Andrey_3a30de", "top_Giulio_89e765", "top_Jesse_5adca6",
        "tape_Crop_Dusta_104547425", "tape_OceanMix_104547425"]


def one(job):
    name, spec, opp, seed, seat = job
    import fidelity, engine
    # 复用 fidelity.play 但需要首店:自己跑一遍轻量版
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    a = [None, None]
    a[seat] = fidelity.make_agent(spec)
    a[1 - seat] = fidelity.make_agent(f"tape:{TAPES}/{opp}.json")
    first_shop = None
    step = 0
    fallback = {"farmer": ["PASS"], "hands": [], "market": []}
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        if first_shop is None and step >= 73:
            cur = (obs[0].get("town") or {}).get("unlocked_shops") or []
            if cur:
                s = cur[0]
                first_shop = s if isinstance(s, str) else s.get("name", str(s))
        acts = []
        for p in (0, 1):
            try:
                acts.append(a[p](obs[p]))
            except Exception:
                acts.append(dict(fallback))
        g.step(acts[0], acts[1])
        step += 1
    bank = [float(g.reward(0)), float(g.reward(1))]
    return {"cand": name, "opp": opp, "seed": seed, "seat": seat,
            "my": bank[seat], "their": bank[1 - seat], "first_shop": first_shop}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    cands = [c.split("=", 1) for c in sys.argv[2].split(",")]
    s0, sn = int(sys.argv[3]), int(sys.argv[4])
    seeds = list(range(s0, s0 + sn))
    jobs = [(n, spec, o, sd, seat) for n, spec in cands for o in OPPS for sd in seeds for seat in (0, 1)]
    print(f"{len(jobs)} games ...", flush=True)
    done = 0
    with out.open("w") as f, ProcessPoolExecutor(8) as ex:
        for r in ex.map(one, jobs, chunksize=4):
            f.write(json.dumps(r) + "\n")
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)
    print("done ->", out)
