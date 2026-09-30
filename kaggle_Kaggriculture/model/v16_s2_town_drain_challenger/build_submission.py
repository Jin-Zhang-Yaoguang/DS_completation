"""Build the V16 A2 + town-drain WHEAT roundtrip challenger."""

from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
PARENT = MODEL_ROOT / "v1_adaptive_market" / "main.py"
MAIN = HERE / "main.py"
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"


OVERLAY = r'''

# --- V16 S2: conservative one-step town-drain WHEAT roundtrip ---
_V16_PARENT_AGENT = agent
_V16_PENDING = {0: None, 1: None}
_V16_LAST_STEP = {0: -1, 1: -1}
_V16_DEMAND_FLOOR = 2
_V16_Q_CAP = 80
_V16_MIN_PROFIT = 2
_V16_CASH_FLOOR = 3000
__version__ = "v16-s2-town-drain-challenger"


def _v16_has_unit_op(action, ops):
    orders = [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]
    return any(isinstance(order, list) and order and order[0] in ops for order in orders)


def _v16_profit(inventory, quantity, demand):
    cost = sum(_market_price("WHEAT", level)
               for level in range(inventory - quantity, inventory))
    revenue = sum(_market_price("WHEAT", level)
                  for level in range(inventory - quantity - demand,
                                     inventory - demand))
    return int(revenue - cost), int(cost)


def _v16_s2(obs, action, step, seat):
    if step == 0 or step < _V16_LAST_STEP[seat]:
        _V16_PENDING[seat] = None
    _V16_LAST_STEP[seat] = step

    pending = _V16_PENDING[seat]
    if pending is not None:
        _V16_PENDING[seat] = None
        available = int((_get(obs, "private", {}) or {}).get("shed", {}).get("WHEAT", 0) or 0)
        available -= _v17_pickup_reserve(action, "WHEAT")
        sold = max(0, min(int(pending), available))
        if sold > 0 and len(action.get("market") or []) < 10:
            action["market"] = [["SELL", "WHEAT", sold], *(action.get("market") or [])]
        return action

    if step >= 718 or step % 4 != 0 or action.get("market"):
        return action
    demand = int(_v17_town_demand_at(obs, "WHEAT", step) or 0)
    if demand < _V16_DEMAND_FLOOR or step + 1 >= len(_ACTIONS):
        return action
    next_base = _ACTIONS[step + 1]
    if next_base.get("market") or _v16_has_unit_op(next_base, {"PICKUP", "DROP", "PLACE"}):
        return action

    projected = _projected_shed(obs, action)
    room = max(0, 100 - sum(max(0, int(value or 0)) for value in projected.values()))
    farm = _farm(obs, seat)
    money = float(_get(farm, "money", 0) or 0)
    market = _get(obs, "market", {}) or {}
    inventory = int((_get(market, "inventory", {}) or {}).get("WHEAT", 0) or 0)
    candidates = []
    for quantity in range(1, min(_V16_Q_CAP, room) + 1):
        profit, cost = _v16_profit(inventory, quantity, demand)
        if money - cost >= _V16_CASH_FLOOR:
            candidates.append((profit, -quantity, cost))
    if not candidates:
        return action
    best_profit = max(row[0] for row in candidates)
    best_quantity = -max(row for row in candidates if row[0] == best_profit)[1]
    if best_profit < _V16_MIN_PROFIT:
        return action
    action["market"] = [["BUY_PRODUCT", "WHEAT", best_quantity]]
    _V16_PENDING[seat] = best_quantity
    return action


del agent


def agent(obs, configuration=None):
    del configuration
    seat = _seat(obs)
    step = int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)
    action = _V16_PARENT_AGENT(obs)
    try:
        return _align_hands(_v16_s2(obs, _copy_action(action), step, seat), obs)
    except Exception:
        return action
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_archive(source: bytes) -> None:
    tar_buffer = BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
        info = tarfile.TarInfo("main.py")
        info.size = len(source)
        info.mode = 0o644
        info.mtime = info.uid = info.gid = 0
        info.uname = info.gname = ""
        tar.addfile(info, BytesIO(source))
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0, compresslevel=9) as zipped:
            zipped.write(tar_buffer.getvalue())


def build() -> dict:
    parent_text = PARENT.read_text(encoding="utf-8")
    if "__file__" in parent_text:
        raise RuntimeError("parent violates raw-loader contract")
    MAIN.write_text(parent_text.rstrip() + "\n" + OVERLAY.lstrip(), encoding="utf-8")
    source = MAIN.read_bytes()
    _write_archive(source)
    with tarfile.open(ARCHIVE, "r:gz") as tar:
        members = tar.getmembers()
        if [member.name for member in members] != ["main.py"]:
            raise RuntimeError("unexpected archive members")
        extracted = tar.extractfile(members[0])
        if extracted is None or extracted.read() != source:
            raise RuntimeError("archive content mismatch")
    from kaggle_environments.agent import get_last_callable
    loaded = get_last_callable(MAIN.read_text(encoding="utf-8"), path=str(MAIN))
    if getattr(loaded, "__name__", None) != "agent":
        raise RuntimeError("raw loader did not select V16 agent")
    result = {
        "schema": "kaggriculture-v16-s2-submission-1",
        "model_id": "v16_s2_town_drain_challenger",
        "parent": str(PARENT.relative_to(MODEL_ROOT)),
        "parent_sha256": sha256(PARENT),
        "main_sha256": sha256(MAIN),
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "members": ["main.py"],
        "raw_loader_callable": getattr(loaded, "__name__", None),
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
