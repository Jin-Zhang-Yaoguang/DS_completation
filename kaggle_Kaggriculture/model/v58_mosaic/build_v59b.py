"""v59b 组装:v58_main.py + 马赛克 T1/T2/T3(T4 回退原版)+ 尾盘清算层。
产出 scratchpad/v59b_main.py。
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad")

src = (SCRATCH / "v58_main.py").read_text()
anchor = "SCHEDULES[0] = _j.loads(_MOSAIC_T0)"
assert anchor in src
inject = [anchor]
for i in (1, 2, 3):
    acts = json.load(open(HERE / f"mosaic_t{i}.json"))["actions"]
    s = json.dumps(json.dumps(acts, separators=(",", ":")))
    inject.append(f"_MOSAIC_T{i} = {s}")
    inject.append(f"SCHEDULES[{i}] = _j.loads(_MOSAIC_T{i})")
out = src.replace(anchor, "\n".join(inject))
assert "_LEAD_AHEAD = 3" in out
out = out.replace("_LEAD_AHEAD = 3", "_LEAD_AHEAD = 5")

LAYER = '''

# ==================== v59 层:尾盘清算(t>=705 shed 剩货补挂 SELL) ====================
_BASE_AGENT_V59 = agent


def agent(observation, configuration=None):
    act = _BASE_AGENT_V59(observation, configuration)
    try:
        turn = int(observation['step']) if 'step' in observation else int(observation['day']) * 24 + int(observation['hour'])
        if turn >= 700:
            priv = observation.get('private') or {}
            shed = dict(priv.get('shed') or {})
            market = [list(o) for o in (act.get('market') or []) if o]
            selling = {o[1] for o in market if o and o[0] == 'SELL' and len(o) > 1}
            for item, qty in sorted(shed.items(), key=lambda kv: -int(kv[1] or 0)):
                if len(market) >= 10:
                    break
                try:
                    q = int(qty)
                except Exception:
                    continue
                if q > 0 and item not in selling:
                    market.append(['SELL', item, q])
            act['market'] = market
    except Exception:
        pass
    return act
'''
out += LAYER
(SCRATCH / "v59b_main.py").write_text(out)
print("v59b_main.py written,", len(out), "bytes")
