"""录制:调度器跑一局(vs 指定对手),动作流存为 tape。"""
import sys, json, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
import engine, fidelity

def record(seed, opp_spec="pass:", cfg_path="best_cfg.json", out=None):
    spec = importlib.util.spec_from_file_location("sched", HERE / "scheduler.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    cfg = json.load(open(HERE / cfg_path))["cfg"]
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    s = m.Sched(m.Cfg(**cfg))
    opp = fidelity.make_agent(opp_spec)
    acts = []
    while not engine._val(g.done) and len(acts) < 720:
        obs0 = g.observe(0); obs0["player"] = 0
        obs1 = g.observe(1)
        a = s.act(obs0)
        acts.append(json.loads(json.dumps(a)))
        try:
            b = opp(obs1)
        except Exception:
            b = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(a, b)
    while len(acts) < 720:
        acts.append({"farmer": ["PASS"], "hands": [], "market": []})
    out = out or (HERE / f"gen_s{seed}.json")
    json.dump({"actions": acts, "gen": {"seed": seed, "opp": opp_spec, "bank": float(g.reward(0))}}, open(out, "w"))
    print(f"recorded seed={seed} opp={opp_spec} bank={g.reward(0):.0f} -> {out}")
    return out

if __name__ == "__main__":
    sd = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    opp = sys.argv[2] if len(sys.argv) > 2 else "pass:"
    record(sd, opp)
