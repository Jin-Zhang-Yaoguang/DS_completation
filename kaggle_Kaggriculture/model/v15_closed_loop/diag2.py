import sys, json, os
H = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v4_demand_race/harness"
sys.path.insert(0, H); os.chdir(H)
from engine import fresh_agent, play
W = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture"
idx = int(sys.argv[1]); sc = json.load(open("scenarios_64.json"))[idx]
c = fresh_agent(f"{W}/model/v15_closed_loop/main.py"); o = fresh_agent(f"{W}/model/v10_rule_distill/dist/main.py")
b0, b1 = play(c.agent, o.agent, sc["seed"], sc["shops"])
print(f"scenario {idx}: {b0:.0f} vs V10 {b1:.0f} ({b0-b1:+.0f})")
