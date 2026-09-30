"""OceanMix tape 重放 agent vs V76/V20，kagsim 双席位。"""
import json, importlib.util, time
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
W = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/community-research-baseline-54669e/kaggle_Kaggriculture"
k = load(f"{W}/model/community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim/kagsim.cpython-312-darwin.so", "kagsim")
TAPE = json.load(open("/tmp/oceanmix_tape.json"))["tape"]

def make_tape_agent():
    def agent(obs):
        t = obs["day"] * 24 + obs["hour"]
        if t >= len(TAPE):
            return {"farmer": ["PASS"], "hands": [], "market": []}
        a = dict(TAPE[t])
        # 最小守卫：hands 数对齐（防越界）
        n = len(obs["farms"][obs["player"]].get("hands") or [])
        h = list(a.get("hands") or [])
        a["hands"] = (h + [["PASS"]] * n)[:n]
        return a
    return agent

def val(x): return x() if callable(x) else x
for name, path in [("V76", f"{W}/model/v76_adjacent_safe_buy_lead/main.py"),
                   ("V20", f"{W}/model/v20_demand_timing_moe/main.py")]:
    wins = 0; ms = []
    for seed in [11, 42, 77, 101, 202, 303]:
        for seat in (0, 1):
            opp = load(path, f"opp_{name}_{seed}_{seat}")
            me = make_tape_agent()
            g = k.Game(seed=seed)
            while not val(g.done):
                a0 = me(g.observe(0)) if seat == 0 else opp.agent(g.observe(0))
                a1 = opp.agent(g.observe(1)) if seat == 0 else me(g.observe(1))
                g.step(a0, a1)
            r_me, r_op = g.reward(seat), g.reward(1 - seat)
            wins += r_me > r_op; ms.append(r_me - r_op)
    ms.sort()
    print(f"tape vs {name}: {wins}/12 胜, margin med={ms[len(ms)//2]:+.0f}, min={ms[0]:+.0f}, max={ms[-1]:+.0f}")
