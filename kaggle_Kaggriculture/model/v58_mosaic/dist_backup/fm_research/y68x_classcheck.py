"""核实 y68x 对手分类与路线选择:FM|YARN / BAKERY|FM seed,对 V43、V43+B10、V38。"""
import sys, json, importlib.util
from pathlib import Path
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
import fidelity, engine
by = json.load(open(S / "combo_seeds_y68v.json"))
OPPS = {"V43": "kernels_0915/v43_agent.py", "V43+B10": "kernels_0915/v43b10_agent.py", "V38原版": "kernels_0913/v38_main.py"}
for combo in ("FARMERS_MARKET|YARN_STORE", "BAKERY|FARMERS_MARKET"):
    for i, sd in enumerate(by[combo][:2]):
        seat = i % 2
        for oname, opath in OPPS.items():
            spec = importlib.util.spec_from_file_location(f"mx{sd}{oname}".replace("+", ""), f"{S}/y68x_main.py")
            mx = importlib.util.module_from_spec(spec); spec.loader.exec_module(mx)
            me = mx._Y68X_ENTRY; op = fidelity.make_agent(f"sub:{S}/{opath}")
            orig_router = mx._IMPL.chassis.router; calls = []
            def spy(observation, step, state, _r=orig_router):
                if step <= 3: calls.append(step)
                return _r(observation, step, state)
            mx._IMPL.chassis.router = spy
            k = engine.load_kagsim(); g = k.Game(seed=sd); cls_at = {}
            for t in range(150):
                acts = [None, None]; acts[seat] = me(g.observe(seat)); acts[1 - seat] = op(g.observe(1 - seat))
                if t in (1, 2, 3): cls_at[t] = dict(mx._Y68X_OPP)
                g.step(acts[0], acts[1])
            route = (mx._IMPL.chassis.players.get(seat) or {}).get("route")
            want = (mx._Y68X_TABLE.get(tuple(combo.split("|"))) or {})
            print(f"{combo:28s} seed{sd} seat{seat} vs {oname:8s}: 路由被调用的步 {calls} | 分类 t1{cls_at.get(1)} t2{cls_at.get(2)} t3{cls_at.get(3)} | 选中 route {route} | 决策表 {want}")
