"""仅统计已校验的 R0/R4/R5 动作带；不导入环境或候选、不重跑对局。"""
import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOVES = {"NORTH", "SOUTH", "WEST", "EAST"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(name):
    base = ROOT / name
    manifest = json.loads((base / "audit_manifest.json").read_text())
    source = Path(manifest["source_trace"]["path"])
    assert digest(source) == manifest["source_trace"]["sha256"]
    trace = json.loads(gzip.open(source, "rt").read())
    seat = trace["candidate_seat"]
    seat_analysis = json.loads((base / "analysis.json").read_text())["seats"][seat]
    findings = json.loads((base / "findings.json").read_text())["seats"][seat]
    sequences = collections.defaultdict(list)
    daily = collections.defaultdict(collections.Counter)
    for step, pair in enumerate(trace["actions"]):
        action = pair[seat]
        day = step // 24
        for owner, op in enumerate([action["farmer"]] + action.get("hands", [])):
            sequences[day, owner].append((step, op))
            daily[day][op[0]] += 1
    pickups = []
    movement_to_pickup = set()
    movement_from_pickup_to_feed = set()
    for (day, owner), sequence in sequences.items():
        for index, (step, op) in enumerate(sequence):
            if op[:2] != ["PICKUP", "WHEAT"]:
                continue
            before = []
            cursor = index - 1
            next_step = step
            while cursor >= 0 and sequence[cursor][0] == next_step - 1 and sequence[cursor][1][0] in MOVES:
                next_step = sequence[cursor][0]
                before.append(next_step)
                cursor -= 1
            after = []
            cursor = index + 1
            last_step = step
            while cursor < len(sequence) and sequence[cursor][0] == last_step + 1 and sequence[cursor][1][0] in MOVES:
                last_step = sequence[cursor][0]
                after.append(last_step)
                cursor += 1
            feeds_next = (cursor < len(sequence) and sequence[cursor][0] == last_step + 1
                          and sequence[cursor][1][0] == "FEED")
            movement_to_pickup.update((s, owner) for s in before)
            if feeds_next:
                movement_from_pickup_to_feed.update((s, owner) for s in after)
            pickups.append({"day": day, "owner": owner, "decision_step": step,
                            "quantity": op[2], "consecutive_moves_before_pickup": len(before),
                            "next_nonmove_action": sequence[cursor][1] if cursor < len(sequence) else None,
                            "feed_after_only_moves": feeds_next,
                            "consecutive_moves_to_feed": len(after) if feeds_next else None})
    counts = collections.Counter(row["quantity"] for row in pickups)
    for row in pickups:
        daily[row["day"]]["wheat_pickup_count"] += 1
        daily[row["day"]]["wheat_pickup_quantity"] += row["quantity"]
        daily[row["day"]]["moves_before_wheat_pickup"] += row["consecutive_moves_before_pickup"]
        if row["feed_after_only_moves"]:
            daily[row["day"]]["moves_pickup_to_feed"] += row["consecutive_moves_to_feed"]
    for row in findings["crop_drought_losses"]:
        daily[row["day"]]["crop_drought_losses"] += 1
    d = seat_analysis["denominators"]
    out = {"name": name, "source_trace_sha256": digest(source),
           "candidate_sha256": manifest["candidate_entry_sha256"], "seed": trace["seed"], "seat": seat,
           "cash": json.loads((base / "analysis.json").read_text())["cash_result"][seat],
           "movement_total": sum(findings["unit_action_counts"].get(k, 0) for k in MOVES),
           "wheat_pickup_count": len(pickups), "wheat_pickup_quantity": sum(row["quantity"] for row in pickups),
           "pickup_quantity_distribution": dict(sorted(counts.items())),
           "moves_in_runs_ending_in_wheat_pickup": len(movement_to_pickup),
           "pickup_then_only_moves_then_feed_count": sum(row["feed_after_only_moves"] for row in pickups),
           "moves_in_pickup_then_only_moves_then_feed": len(movement_from_pickup_to_feed),
           "union_moves_adjacent_to_pickup": len(movement_to_pickup | movement_from_pickup_to_feed),
           "feed": findings["unit_action_counts"].get("FEED", 0),
           "water": findings["unit_action_counts"].get("WATER", 0),
           "care": findings["unit_action_counts"].get("CARE", 0),
           "drought_still_productive": findings["drought_loss_still_productive_count"],
           "animal_unfed_eod": d["animal_unfed_eod_exposures"],
           "animal_eod_exposures": d["animal_eod_exposures"],
           "overflow": seat_analysis["overflow"], "terminal_assets": seat_analysis["terminal_assets"],
           "daily": dict(sorted(daily.items())), "pickups": pickups}
    assert len(movement_to_pickup | movement_from_pickup_to_feed) <= out["movement_total"]
    return out


def main():
    result = {"schema": "v125-opened-trace-feed-workload-v1", "script_sha256": digest(Path(__file__)),
              "candidate_calls": 0, "engine_runs": 0,
              "definitions": {
                  "unit_day": "同一 day 与单位编号，不跨日连接雇工轨迹。",
                  "pickup": "已发出的 PICKUP WHEAT 请求，数量为请求数量；来源分析确认全部非空动作均发生状态变化，但此统计不额外声称逐次足额领取。",
                  "movement": "只计无间断 MOVE 段：以领取结束或以领取开始且下一非移动动作为 FEED；不跨日、不跨缺失动作。",
                  "attribution": "行动邻接关联，不是全部粮食物流成本，更不证明这些步数都可节约或某株死亡由取粮直接造成。"},
              "candidates": [analyze(name) for name in ("r0_pass_s0", "r4_pass_s0", "r5_pass_s0")]}
    path = ROOT / "r5_feed_workload.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps([{k: v for k, v in row.items() if k not in {"daily", "pickups", "overflow", "terminal_assets"}}
                      for row in result["candidates"]], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
