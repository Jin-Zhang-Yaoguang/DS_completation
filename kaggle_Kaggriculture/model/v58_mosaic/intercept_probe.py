"""截胡实验:v59b + 无条件 yhay 表截胡层 vs v57。用法: python intercept_probe.py <seed> <ahead>"""
import sys, os, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = "/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad"
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
os.chdir(f"{S}/yhay81_0908_extract")
import engine

PREM = ("STRAWBERRY", "MILK", "WOOL", "MELON", "EGG")
ytab = {}
for i in range(4):
    acts = json.load(open(HERE.parent / "v16_online_fidelity" / "tapes" / f"pub_yhay_{i}.json"))["actions"]
    for t, a in enumerate(acts):
        for o in (a.get("market") or []):
            if o and o[0] == "SELL" and len(o) > 2 and o[1] in PREM:
                ytab.setdefault(t, []).append((o[1], o[2]))

def run(sd, ahead):
    ns = {}
    exec(Path(f"{S}/v59b_main.py").read_text(), ns)
    base = [v for k, v in ns.items() if callable(v) and not k.startswith("__")][-1]

    def ag(obs):
        act = base(obs)
        try:
            turn = int(obs["step"]) if "step" in obs else int(obs["day"]) * 24 + int(obs["hour"])
            priv = obs.get("private") or {}
            shed = dict(priv.get("shed") or {})
            market = [list(o) for o in (act.get("market") or []) if o]
            selling = {o[1] for o in market if o and o[0] == "SELL" and len(o) > 1}
            for da in range(1, ahead + 1):
                for item, qty in ytab.get(turn + da, []):
                    if len(market) >= 10:
                        break
                    have = int(shed.get(item) or 0)
                    if have > 0 and item not in selling:
                        market.append(["SELL", item, min(have, int(qty))])
                        selling.add(item)
            act["market"] = market
        except Exception:
            pass
        return act

    ns7 = {}
    exec(Path(f"{S}/yhay81_0908_extract/v57_main.py").read_text(), ns7)
    ag7 = [v for k, v in ns7.items() if callable(v) and not k.startswith("__")][-1]
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    for step in range(719):
        o0 = g.observe(0); o0["player"] = 0
        o1 = g.observe(1); o1["player"] = 1
        try: a = ag(o0)
        except Exception: a = {"farmer": ["PASS"], "hands": [], "market": []}
        try: b = ag7(o1)
        except Exception: b = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(a, b)
    return g.reward(0) - g.reward(1)

if __name__ == "__main__":
    sd = int(sys.argv[1]) if len(sys.argv) > 1 else 501
    ahead = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    print(f"seed{sd} ahead={ahead}: {run(sd, ahead):+.0f}", flush=True)
