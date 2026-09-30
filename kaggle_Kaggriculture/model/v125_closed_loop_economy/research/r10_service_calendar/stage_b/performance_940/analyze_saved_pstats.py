"""只读取已存 pstats 并导出父调用边；不导入或运行候选。"""
import hashlib
import json
from pathlib import Path
import pstats

HERE = Path(__file__).resolve().parent
RUN = HERE / "run_once"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key_json(key):
    return {"file": key[0], "line": key[1], "function": key[2]}


def main():
    stats = pstats.Stats(str(RUN / "raw.pstats"))
    targets = {
        "deepcopy", "dumps", "budget_quote", "economic_plan_prefix", "prefix_admission",
        "_r10_scheduler_schedule_day", "_r10_checker_check_day", "_r10_checker_canonical_hash",
        "_r10_route_admission_route_admission", "_r10_calendar_compiler_compile_day_problem",
        "_r10_calendar_compiler_project_calendar_with_services", "_r10_integration_quote_calendar",
        "_r10_integration_actual_calendars", "_r10_integration_register_quote", "_r10_integration_finish",
        "_r10_integration_compact_result", "_r10_calendar_compiler_canonical_sha",
        "_r10_scheduler_canonical_sha", "free_assignment", "remaining", "projected_group_cost",
    }
    records = []
    absent = set(targets)
    for key, (primitive, total, own, cumulative, callers) in stats.stats.items():
        if key[2] not in targets:
            continue
        absent.discard(key[2])
        edges = []
        for caller, raw in callers.items():
            # cProfile 的 caller tuple 顺序为 total, primitive, self, cumulative。
            edges.append({"caller": key_json(caller), "total_calls": raw[0], "primitive_calls": raw[1],
                          "self_seconds": raw[2], "cumulative_seconds": raw[3], "raw_cprofile_tuple": raw})
        edges.sort(key=lambda x: -x["cumulative_seconds"])
        records.append({**key_json(key), "primitive_calls": primitive, "total_calls": total,
                        "self_seconds": own, "cumulative_seconds": cumulative,
                        "cumulative_fraction_of_total_profile_self": cumulative / stats.total_tt,
                        "callers": edges})
    records.sort(key=lambda x: -x["cumulative_seconds"])
    deepcopy = next(row for row in records if row["function"] == "deepcopy")
    nonrecursive = [row for row in deepcopy["callers"] if not row["caller"]["file"].endswith("/copy.py")]
    result = {
        "schema": "r10-performance-940-parent-edges-v1", "raw_pstats_sha256": sha(RUN / "raw.pstats"),
        "summary_sha256": sha(RUN / "summary.json"), "source_sha256": sha(HERE / "prototype_940.py"),
        "profile_total_self_seconds": stats.total_tt, "selected_functions": records,
        "selected_functions_without_recorded_entry": sorted(absent),
        "deepcopy_non_copy_py_parent_edges": nonrecursive,
        "deepcopy_non_copy_py_parent_cumulative_sum": sum(row["cumulative_seconds"] for row in nonrecursive),
        "scope": "只读单次中断执行前缀；pstats父边按函数聚合，不能辨别同函数不同源码行或单个报价身份。累计时间有嵌套，不跨层相加。",
        "new_calls": {"candidate_definition_loads": 0, "economic": 0, "agent": 0, "engine": 0, "scheduler": 0, "checker": 0},
    }
    (HERE / "parent_edges.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"raw_pstats_sha256": result["raw_pstats_sha256"],
                      "deepcopy_non_copy_py_parent_cumulative_sum": result["deepcopy_non_copy_py_parent_cumulative_sum"],
                      "absent": result["selected_functions_without_recorded_entry"], "new_calls": result["new_calls"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
