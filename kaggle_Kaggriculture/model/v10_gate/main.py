"""V10 门控适配：v10_replay_lolo_router 的 learned_router（专家 v1/v2/v5/v8，step72 切换）→ agent(obs)。"""
import importlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
V10 = os.path.abspath(os.path.join(HERE, "..", "v10_replay_lolo_router"))
if V10 not in sys.path:
    sys.path.insert(0, V10)
MODEL_ID = os.environ.get("V10_MODEL", "learned_router")
_af = importlib.import_module("agent_factory")           # 常规导入，dataclass 需要 sys.modules 注册
_reg = _af.load_registry(os.path.join(V10, "final_registry.json"))
_handle = _af.create_agent(_reg, MODEL_ID)

def agent(obs, configuration=None):
    try:
        return _handle(obs, configuration)
    except Exception:
        farms = obs.get("farms") or []; player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}
