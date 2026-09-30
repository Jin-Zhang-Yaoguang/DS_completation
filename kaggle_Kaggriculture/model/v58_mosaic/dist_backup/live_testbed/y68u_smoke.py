"""y68u 冒烟:对 V41 跑一局(新带组合 seed + YARN seed),读取 V43 各层计数器,确认层在工作且无错误。"""
import sys, json, importlib.util
from pathlib import Path
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
import fidelity, engine, time
rows = json.load(open(S / "y68s2_check.json"))["y68s2"]
seeds = []
for want_yarn in (False, True):
    r = next(x for x in rows if x["yarn"] == want_yarn and not x["bl"])
    seeds.append((json.load(open(S / f"live_replays3/episode-{r['ep']}-replay.json"))["info"]["seed"], r["shops"]))
for sd, shops in seeds:
    spec = importlib.util.spec_from_file_location(f"mu{sd}", f"{S}/y68u_main.py")
    mu = importlib.util.module_from_spec(spec); spec.loader.exec_module(mu)
    me = mu._Y68U_ENTRY
    op = fidelity.make_agent(f"sub:{S}/kernels_0914/v41_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd); t0 = time.time(); worst = 0.0
    while not engine._val(g.done):
        a = time.time(); x = me(g.observe(0)); worst = max(worst, time.time() - a)
        g.step(x, op(g.observe(1)))
    print(f"\nseed{sd} {shops}: y68u vs V41 margin {g.reward(0)-g.reward(1):+.0f}  route={mu._IMPL.chassis.players.get(0,{}).get('route')}  单步最慢 {worst*1000:.0f}ms  全局 {time.time()-t0:.0f}s")
    for name in sorted(k for k in vars(mu) if re.match(r"_R\d+_REPORT$", k)) if False else sorted(k for k in vars(mu) if k.startswith("_R") and k.endswith("_REPORT")):
        rep = getattr(mu, name)
        if isinstance(rep, dict) and rep:
            errs = {k: v for k, v in rep.items() if "error" in k and v}
            acts = {k: v for k, v in rep.items() if "error" not in k and isinstance(v, (int, float)) and v}
            print(f"   {name}: 错误{errs if errs else '无'} | 非零计数 {dict(list(acts.items())[:6])}")
