"""从 Majkel 原始回放生成 tape 对手（tape 层「难」考官：不反应、但产出节奏为榜首水平）。
actions[k] = steps[k+1][seat].action（在 turn k 的观测上做出的动作），与 fidelity.tape_agent 的 t=day*24+hour 对齐。
用法: /opt/anaconda3/bin/python3 build_majkel_tapes.py [n]
"""
import json, sys
from pathlib import Path
from scale_distill import IDX, V71
OUT = Path(__file__).resolve().parent / "opp_tapes"
n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
made = []
with open(V71 / "majkel_0910_12.jsonl") as f:
    for line in f:
        g = json.loads(line)
        fp = IDX / g["date"] / "data" / f"{g['ep']}.json"
        if not fp.exists():
            continue
        rep = json.loads(fp.read_text())
        names = (rep.get("info") or {}).get("TeamNames") or []
        if "Majkel1337" not in names:
            continue
        seat = names.index("Majkel1337")
        steps = rep["steps"]
        acts = [steps[k + 1][seat].get("action") or {} for k in range(len(steps) - 1)]
        rew = [steps[-1][i].get("reward") for i in range(2)]
        name = f"majkel_{g['ep']}.json"
        (OUT / name).write_text(json.dumps({"team": "Majkel1337", "ep": g["ep"], "opp": names[1 - seat],
                                            "final": rew, "actions": acts}))
        made.append((name, names[1 - seat], rew))
        if len(made) >= n:
            break
for m in made:
    print(m)
