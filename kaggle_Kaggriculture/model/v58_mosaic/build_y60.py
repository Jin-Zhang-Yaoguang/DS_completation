"""y60 组装:v57(yhay 底盘)单文件化 + LEAD 3->5 + 尾盘清算层。
tapes 可选替换(马赛克):python build_y60.py [mosaic_y0.json ...] 按序替换 tape0..3。
产出 scratchpad/y60_main.py。
"""
import sys, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad")
EXT = SCRATCH / "yhay81_0908_extract"

model_s = (EXT / "model.json").read_text()
tapes = json.loads((EXT / "actions.json").read_text())
# 马赛克替换:每个参数是 {"tape_idx": i, "actions": [...]} 或纯 actions 列表(按位次)
for k, arg in enumerate(sys.argv[1:]):
    d = json.load(open(arg))
    idx = d.get("tape_idx", k) if isinstance(d, dict) else k
    acts = d["actions"] if isinstance(d, dict) else d
    assert len(acts) == 719, f"{arg}: {len(acts)} != 719"
    tapes[idx] = acts
    print(f"tape{idx} <- {arg}")
actions_s = json.dumps(tapes, separators=(",", ":"))
obs_src = (EXT / "observation.py").read_text()

src = (EXT / "v57_main.py").read_text()
reps = [
    ('self.folder = Path(folder)', 'self.folder = None'),
    ('self.model = json.loads((self.folder / "model.json").read_text())',
     'self.model = json.loads(_MODEL_JSON)'),
    ('self.tapes = json.loads((self.folder / "actions.json").read_text())',
     'self.tapes = json.loads(_ACTIONS_JSON)'),
    ('self.observation_module = load_module(self.folder / "observation.py", "mmpq_observation")',
     'self.observation_module = _OBS_MOD'),
    ('_ROUTER = Router(Path(agent.__code__.co_filename).resolve().parent)',
     '_ROUTER = Router(None)'),
    ('for da in range(1, 4):', 'for da in range(1, 6):'),
]
for old, new in reps:
    assert old in src, old
    src = src.replace(old, new)

fut = "from __future__ import annotations\n"
assert fut in src
src = src.replace(fut, "")
prefix = "".join([
    fut,
    "_MODEL_JSON = ", json.dumps(model_s), "\n",
    "_ACTIONS_JSON = ", json.dumps(actions_s), "\n",
    "_OBS_SRC = ", json.dumps(obs_src), "\n",
    "import types as _types\n",
    "_OBS_MOD = _types.ModuleType('mmpq_observation')\n",
    "exec(_OBS_SRC, _OBS_MOD.__dict__)\n",
])

LAYER = '''

# ==================== y60 层:尾盘清算(t>=700 shed 剩货补挂 SELL) ====================
_BASE_AGENT_Y60 = agent


def agent(observation, configuration=None):
    act = _BASE_AGENT_Y60(observation, configuration)
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

out = prefix + src + LAYER
(SCRATCH / "y60_main.py").write_text(out)
print("y60_main.py written,", len(out), "bytes")
