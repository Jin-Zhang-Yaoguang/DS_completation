"""固定路由探测:v59b 强制走 route i,打 v57@seed。用法: python route_probe.py <seed>"""
import sys, os, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
S = "/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad"

def one(job):
    route, sd = job
    os.chdir(f"{S}/yhay81_0908_extract")
    sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
    sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
    import engine
    ns = {}
    exec(Path(f"{S}/v59b_main.py").read_text(), ns)
    # 强制路由:route_for 恒返 route
    ns["route_for"] = (lambda r: (lambda block, obs, cur: r))(route)
    ag = [v for k, v in ns.items() if callable(v) and not k.startswith("__")][-1]
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
    return (route, sd, g.reward(0) - g.reward(1))

if __name__ == "__main__":
    sd = int(sys.argv[1]) if len(sys.argv) > 1 else 501
    jobs = [(r, sd) for r in range(5)]
    with ProcessPoolExecutor(5) as ex:
        for route, s, m in ex.map(one, jobs):
            print(f"route{route} seed{s}: {m:+.0f}", flush=True)
