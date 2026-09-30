"""V9：精确 V120 + PASS 填充（零副作用 ε 生产）。
V120 输出中单位动作为 PASS 时，若该单位脚下有未浇水的作物 → WATER；有未 CARE 的动物 → CARE；
（可选 V9_FERT=1：有可收肥料且 shed 有余量 → COLLECT_FERTILIZER）。不移动、不改市场单。
镜像局是平局；任何正的 ε 都能把平局变成小胜。可叠加 V8 羊毛对冲（V9_HEDGE=1）。"""
import importlib.util, os
HERE = os.path.dirname(os.path.abspath(__file__))
V120_PATH = os.path.join(HERE, "..", "v120_hierarchical_top5_distillation", "main.py")
FERT = os.environ.get("V9_FERT", "0") == "1"
HEDGE = os.environ.get("V9_HEDGE", "0") == "1"
SKIP_FROM = int(os.environ.get("V8_SKIP_FROM_DAY", "7"))

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

_v120 = _load_module("v9_v120_core", V120_PATH)

def _fill(unit_action, tile, shed_room):
    if not (isinstance(unit_action, list) and unit_action and unit_action[0] == "PASS"):
        return unit_action
    if not isinstance(tile, dict):
        return unit_action
    if tile.get("kind") == "PLANT" and not tile.get("watered_today"):
        return ["WATER"]
    if "animal" in tile:
        if not tile.get("cared_today"):
            return ["CARE"]
        if FERT and tile.get("fertilizer_available") and shed_room > 5:
            return ["COLLECT_FERTILIZER"]
    return unit_action

def agent(obs, configuration=None):
    try:
        base = _v120.agent(obs, configuration)
    except Exception:
        farms = obs.get("farms") or []; player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}
    try:
        player = obs.get("player", 0)
        farm = obs["farms"][player]; tiles = farm["tiles"]; bs = len(tiles)
        shed = (obs.get("private") or {}).get("shed") or {}
        room = 100 - sum(shed.values())
        pos = [tuple(farm["farmer"])] + [tuple(p) for p in (farm.get("hands") or [])]
        units = [base.get("farmer") or ["PASS"]] + list(base.get("hands") or [])
        for i in range(min(len(units), len(pos))):
            x, y = pos[i]
            tile = tiles[y][x] if 0 <= y < bs and 0 <= x < bs else None
            units[i] = _fill(units[i], tile, room)
        base["farmer"] = units[0]; base["hands"] = units[1:]
        if HEDGE:
            day = int(obs.get("day", 0)); shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
            if day >= SKIP_FROM and "YARN_STORE" not in shops:
                base["market"] = [m for m in (base.get("market") or []) if not (m and m[0] == "BUY_ANIMAL" and len(m) > 1 and m[1] == "SHEEP")]
        return base
    except Exception:
        return base
