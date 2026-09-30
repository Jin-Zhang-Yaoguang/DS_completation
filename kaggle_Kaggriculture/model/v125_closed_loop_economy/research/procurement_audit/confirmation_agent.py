"""V22 诊断补丁：只补土地采购的下一帧确认；不是独立原创策略。"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("v22_procurement_frozen_base", HERE / "baseline.py")
BASE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BASE)
_PENDING_TX = {}
AUDIT_EVENTS = []


def agent(obs, configuration=None):
    seat = int(obs.get("player", 0) or 0)
    step = int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)
    farm = obs["farms"][seat]
    land_count = len(farm.get("unlocked_quadrants") or [])
    previous = _PENDING_TX.pop(seat, None)
    if previous is not None and step == previous["step"] + 1:
        actual = max(0, min(previous["requested"], land_count - previous["land_count"]))
        missing = previous["requested"] - actual
        state = BASE._S.get(seat)
        if missing:
            if state is None or state.get("pending") is None:
                raise RuntimeError("缺少土地采购待办，不能静默丢弃未成交交易")
            state["pending"]["land"] += missing
        AUDIT_EVENTS.append({
            "seat": seat, "issued_step": previous["step"], "confirmation_step": step,
            "requested": previous["requested"], "confirmed": actual,
            "restored_pending": missing,
        })
    elif previous is not None and step > previous["step"]:
        raise RuntimeError("确认观测不是连续下一帧，拒绝猜测成交")

    # 直接调用双方相同的调度器主体；不更改预算、订单顺序、单位动作或既有宏观计划。
    action = BASE._agent(obs)
    requested = sum(bool(order and order[0] == "BUY_LAND") for order in action.get("market", []))
    if requested:
        _PENDING_TX[seat] = {"step": step, "requested": requested, "land_count": land_count}
    return action
