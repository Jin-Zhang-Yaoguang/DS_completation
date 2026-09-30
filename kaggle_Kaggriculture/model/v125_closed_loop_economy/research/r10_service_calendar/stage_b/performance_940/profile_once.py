"""冻结输入的一次内部经济函数归因；根签发 release 后才可运行。"""
from __future__ import annotations

import argparse
import cProfile
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import pstats
import signal
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


class ProfileDeadline(Exception):
    """保护触发也消耗唯一一次调用，不重试。"""


def category(filename, line, name, owner_ranges):
    # self 时间按互斥分类相加；累计时间含子调用，分类之间会重叠。
    if filename.endswith("/copy.py"):
        return "deepcopy_and_copy"
    if "/json/" in filename or name in ("<built-in method _json.encode_basestring_ascii>",):
        return "json"
    # 冻结源码的 AST 顶层区间覆盖嵌套函数、方法及推导式，不能仅靠原函数名。
    if filename == str(HERE / "prototype_940.py"):
        for owner in owner_ranges:
            if owner["line"] <= line <= owner["end_line"]:
                return owner["category"]
    return "other"


def export_profile(profile, output, owner_ranges):
    # 先落原始 pstats，再生成可读派生物。中断后的记录不是完整计划画像。
    profile.dump_stats(str(output / "raw.pstats"))
    stats = pstats.Stats(str(output / "raw.pstats"))
    rows = []
    groups = {}
    for (filename, line, name), (primitive, calls, self_s, cumulative_s, callers) in stats.stats.items():
        group = category(filename, line, name, owner_ranges)
        rows.append({"file": filename, "line": line, "function": name,
                     "primitive_calls": primitive, "total_calls": calls,
                     "self_seconds": self_s, "cumulative_seconds": cumulative_s,
                     "category": group})
        bucket = groups.setdefault(group, {"self_seconds": 0.0, "total_calls": 0, "function_count": 0})
        bucket["self_seconds"] += self_s
        bucket["total_calls"] += calls
        bucket["function_count"] += 1
    for bucket in groups.values():
        bucket["self_fraction_of_total_profile_self"] = bucket["self_seconds"] / stats.total_tt if stats.total_tt else 0.0
    rows.sort(key=lambda row: (-row["cumulative_seconds"], row["file"], row["line"], row["function"]))
    save_json(output / "function_stats.json", {
        "scope": "仅本次内部 economic_plan_prefix，可能被中断；累计时间不可跨函数或分类相加。",
        "total_profile_self_seconds": stats.total_tt, "total_calls": stats.total_calls,
        "primitive_calls": stats.prim_calls, "disjoint_self_categories": groups, "functions": rows})
    for sort in ("cumulative", "tottime"):
        stream = io.StringIO()
        pstats.Stats(str(output / "raw.pstats"), stream=stream).sort_stats(sort).print_stats(100)
        (output / ("top_" + sort + ".txt")).write_text(stream.getvalue())
    return {"total_profile_self_seconds": stats.total_tt, "total_calls": stats.total_calls,
            "primitive_calls": stats.prim_calls, "disjoint_self_categories": groups,
            "economic_entries_recorded": sum(row["total_calls"] for row in rows if row["function"] == "economic_plan_prefix")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True, type=Path)
    args = ap.parse_args()
    freeze_raw = (HERE / "freeze_manifest.json").read_bytes()
    freeze = json.loads(freeze_raw)
    release_raw = args.release.read_bytes()
    release = json.loads(release_raw)
    if (release.get("schema") != "r10-performance-940-release-v1"
            or release.get("root_execution_release") is not True
            or release.get("freeze_sha256") != sha(freeze_raw)
            or release.get("run_id") != "day8_funded_s0_single_internal_profile"):
        raise SystemExit("ROOT_RELEASE_MISSING_OR_WRONG_FREEZE")
    for relative, expected in freeze["files"].items():
        if sha((HERE / relative).read_bytes()) != expected:
            raise SystemExit("FROZEN_FILE_CHANGED:" + relative)
    config = json.loads((HERE / "config.json").read_bytes())
    if config["call_limits"] != {"new_state": 1, "internal_economic_plan_prefix": 1, "whole_agent": 0, "engine": 0}:
        raise SystemExit("INVALID_CALL_LIMITS")
    if config["protection_seconds"] != 30 or config["fixture_id"] != "48_strawberries_day8_funded_s0":
        raise SystemExit("INVALID_FIXED_SCOPE")
    fixture = json.loads((HERE / "fixture_case.json").read_bytes())
    full = json.loads((HERE / "fixtures_v1_snapshot.json").read_bytes())
    matches = [case for case in full["cases"] if case["id"] == config["fixture_id"]]
    if len(matches) != 1 or fixture != matches[0]:
        raise SystemExit("CASE_NOT_EXACT_FULL_FIXTURE_MEMBER")
    obs = fixture["observation"]
    if (fixture["seat"], obs["player"], obs["day"], obs["hour"], obs["step"]) != (0, 0, 8, 0, 192):
        raise SystemExit("FIXTURE_CLOCK_OR_SEAT_CHANGED")

    # 固定目录是一次执行锁；任何中断后再次运行都拒绝，不自动清理或重试。
    output = HERE / "run_once"
    output.mkdir(exist_ok=False)
    (output / "release_used.json").write_bytes(release_raw)
    counts = {"source_definition_loads": 0, "new_state": 0, "internal_economic_plan_prefix": 0,
              "whole_agent": 0, "engine_initializations": 0, "engine_steps": 0, "new_matches": 0}
    started_at = datetime.now(timezone.utc).isoformat()
    save_json(output / "invocation.json", {"started_at_utc": started_at, "freeze_sha256": sha(freeze_raw),
              "config": config, "counts_before": counts, "pid": __import__("os").getpid(),
              "python": sys.version, "python_executable": sys.executable})
    prof = cProfile.Profile()
    ns, st, result, error, profile_data, interrupted_stack = None, None, None, None, None, None
    profiled_wall = None
    profile_started = False
    old_handler = signal.getsignal(signal.SIGALRM)

    def expired(signum, frame):
        nonlocal interrupted_stack
        # 先停统计，避免保存中断证据本身被混入热点。
        prof.disable()
        interrupted_stack = "".join(traceback.format_stack(frame))
        (output / "interrupted_stack.txt").write_text(interrupted_stack)
        raise ProfileDeadline("30秒内部经济函数保护；这一次已消耗，不重试")

    try:
        source_path = HERE / "prototype_940.py"
        ns = {"__name__": "r10_performance_940_frozen", "__file__": str(source_path)}
        counts["source_definition_loads"] += 1
        exec(compile(source_path.read_bytes(), str(source_path), "exec"), ns)
        if ns["PARAMS"] != config["expected_params"] or ns.get("_STATES") != {}:
            raise ValueError("DEFAULT_PARAMS_OR_INITIAL_GLOBAL_STATE_CHANGED")
        counts["new_state"] += 1
        st = ns["new_state"](obs)
        signal.signal(signal.SIGALRM, expired)
        counts["internal_economic_plan_prefix"] += 1
        start = time.perf_counter()
        profile_started = True
        signal.setitimer(signal.ITIMER_REAL, config["protection_seconds"])
        prof.enable()
        try:
            result = ns["economic_plan_prefix"](obs, st)
        finally:
            prof.disable()
            signal.setitimer(signal.ITIMER_REAL, 0)
            profiled_wall = time.perf_counter() - start
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        (output / "exception.txt").write_text(error["traceback"])
    finally:
        prof.disable()
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if profile_started:
            try:
                profile_data = export_profile(prof, output, config["source_owner_ranges"])
            except BaseException as exc:
                save_json(output / "profile_export_error.json", {"type": type(exc).__name__, "traceback": traceback.format_exc()})
        drift = [relative for relative, expected in freeze["files"].items()
                 if sha((HERE / relative).read_bytes()) != expected]
        if (HERE / "freeze_manifest.json").read_bytes() != freeze_raw:
            drift.append("freeze_manifest.json")
        state_summary = None if st is None else {"keys": sorted(st), "metrics": dict(st.get("metrics", {})),
              "investment_receipt_count": len(st.get("investment_receipts", []))}
        summary = {"schema": "r10-performance-940-result-v1", "started_at_utc": started_at,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "SOURCE_DRIFT" if drift else ("PROFILE_PROTECTION_INTERRUPTED" if error and error["type"] == "ProfileDeadline" else ("ERROR" if error else "RETURNED")),
            "counts": counts, "freeze_sha256": sha(freeze_raw), "source_drift": drift, "error": error,
            "profiled_wall_seconds_not_pure_strategy_performance": profiled_wall,
            "returned_plan": result is not None, "result_type": type(result).__name__,
            "interrupted_stack_saved": interrupted_stack is not None, "profile": profile_data,
            "state_after_summary": state_summary, "global_agent_states_still_empty": ns is not None and ns.get("_STATES") == {},
            "scope": "一次人工已打开状态的内部 cProfile 归因；未调用完整 agent/引擎。被中断则只反映执行前缀，不能代表完整计划或无 profile 性能。"}
        save_json(output / "summary.json", summary)
        print(json.dumps({key: summary[key] for key in ("status", "counts", "profiled_wall_seconds_not_pure_strategy_performance", "returned_plan", "source_drift")}, ensure_ascii=False))
    return int(bool(error or drift))


if __name__ == "__main__":
    raise SystemExit(main())
