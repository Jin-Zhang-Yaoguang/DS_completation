"""完整动作口径 trace 差异(含 market):cand vs ref 同对手同 seed 各打一局比较。
用法: python trace_full.py <cand> <ref>
"""
import sys, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
import engine, fidelity

def traced(main_path, opp_spec, sd):
    ns = {}
    exec(Path(main_path).read_text(), ns)
    ag = [v for k, v in ns.items() if callable(v) and not k.startswith("__")][-1]
    opp = fidelity.make_agent(opp_spec)
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    acts = []
    for step in range(719):
        obs = g.observe(0); obs["player"] = 0
        try: a = ag(obs)
        except Exception: a = {"farmer": ["PASS"], "hands": [], "market": []}
        acts.append(json.dumps(a, sort_keys=True))
        try: b = opp(g.observe(1))
        except Exception: b = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(a, b)
    return acts, float(g.reward(0))

if __name__ == "__main__":
    cand, ref = sys.argv[1], sys.argv[2]
    opps = ["tape:" + str(HERE.parent / "v51_block_router" / "newpool" / "op_e3bb880a.json"), "pass:"]
    tot_diff, tot = 0, 0
    for opp in opps:
        for sd in (77, 88):
            a1, b1 = traced(cand, opp, sd)
            a2, b2 = traced(ref, opp, sd)
            d = sum(x != y for x, y in zip(a1, a2))
            tot_diff += d; tot += len(a1)
            print(f"opp={Path(opp.partition(':')[2]).stem or 'solo'} seed{sd}: diff {d}/719, cand={b1:.0f} ref={b2:.0f}", flush=True)
    print(f"total: {tot_diff}/{tot} = {tot_diff/tot:.1%}", flush=True)
