"""A 阶段证据实验:候选带 × 对手 × seed 双席位矩阵,记录每局首店(shop world)。
输出 JSONL,供按 (对手, 首店) 分桶分析两带胜率差。
用法: python world_matrix.py <out.jsonl> <cand1,cand2,...> [seeds_start seeds_n]
"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"

OPPS = ["fam_A_0w8l", "fam_B_cornhub", "fam_C_0w5l", "fam_D_0w5l", "fam_E_0w3l",
        "fam_F_new", "fam_G_new", "pert_0_b79742", "pert_1_22ebcc", "pert_2_0f8469",
        "pert_3_597210", "cand_0_ec979a", "cand_1_bf2b55", "cand_2_c333c1",
        "top_keiz_82acad", "top_Andrey_3a30de", "top_Giulio_89e765", "top_Jesse_5adca6",
        "tape_Crop_Dusta_104547425", "tape_OceanMix_104547425"]

_tape_cache = {}


def tape_agent_from(name):
    if name not in _tape_cache:
        _tape_cache[name] = json.load(open(TAPES / f"{name}.json"))["actions"]
    actions = _tape_cache[name]
    def agent(obs):
        t = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
        a = actions[t] if t < len(actions) else {}
        return {"farmer": list(a.get("farmer") or ["PASS"]),
                "hands": [list(h) for h in (a.get("hands") or [])],
                "market": [list(o) for o in (a.get("market") or [])]}
    return agent


def one(job):
    cand, opp, seed, seat = job
    import engine
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    a = [None, None]
    a[seat] = tape_agent_from(cand)
    a[1 - seat] = tape_agent_from(opp)
    first_shop, shops_seen = None, []
    step = 0
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        if step in (73, 145, 217, 361, 505, 577):
            cur = list((obs[0].get("town") or {}).get("unlocked_shops") or [])
            for s in cur:
                nm = s if isinstance(s, str) else s.get("name", str(s))
                if nm not in shops_seen:
                    shops_seen.append(nm)
            if first_shop is None and shops_seen:
                first_shop = shops_seen[0]
        acts = []
        for p in (0, 1):
            try:
                acts.append(a[p](obs[p]))
            except Exception:
                acts.append({"farmer": ["PASS"], "hands": [], "market": []})
        g.step(acts[0], acts[1])
        step += 1
    bank = [float(g.reward(0)), float(g.reward(1))]
    return {"cand": cand, "opp": opp, "seed": seed, "seat": seat,
            "my": bank[seat], "their": bank[1 - seat],
            "first_shop": first_shop, "shops": shops_seen[:3]}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    cands = sys.argv[2].split(",")
    s0 = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    sn = int(sys.argv[4]) if len(sys.argv) > 4 else 64
    seeds = list(range(s0, s0 + sn))
    jobs = [(c, o, sd, seat) for c in cands for o in OPPS for sd in seeds for seat in (0, 1)]
    print(f"{len(jobs)} games ...", flush=True)
    done = 0
    with out.open("w") as f, ProcessPoolExecutor(8) as ex:
        for r in ex.map(one, jobs, chunksize=8):
            f.write(json.dumps(r) + "\n")
            done += 1
            if done % 500 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)
    print("done ->", out)
