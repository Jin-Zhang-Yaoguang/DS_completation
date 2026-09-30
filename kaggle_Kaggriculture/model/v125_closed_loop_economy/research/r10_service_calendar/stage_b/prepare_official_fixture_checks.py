"""官方执行前的纯 fixture/编译/排程检查；不导入官方环境或完整候选。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location("pure_fixture_" + name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    paths = [HERE / n for n in ("SCHEMA.md", "calendar_compiler.py", "scheduler.py", "checker.py", "official_fixtures.py", "test_official_controls.py", Path(__file__).name)]
    source = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    fx, compiler, scheduler, checker = [load(n) for n in ("official_fixtures", "calendar_compiler", "scheduler", "checker")]
    results, failures = [], []
    for case in fx.certificate_fixtures():
        day = case["day"]
        calendars = [compiler.project_calendar_with_services(row["tile"], day, 0, tuple(row["pos"]), case["provenance"]) for row in case["tiles"]]
        a = b = 1; cost = 0
        for _ in range(case["n_hands"]):
            cost += a; a, b = b, a + b
        kwargs = {"day": day, "current_day": day - 1, "start_shed": case["shed"], "reserved_shed": case["reserve"],
                  "planned_wheat_buy": {"qty": case["buy"], "estimated_cash": case["buy"] * 30, "order_hour": 0, "available_from_hour": 1},
                  "legacy_work": sum(c["work"].get(day, 0) for c in calendars), "legacy_hire_cost": cost,
                  "conditional": [case["provenance"]]}
        p = compiler.compile_day_problem(calendars, **kwargs)
        p_before = scheduler.canonical_sha(p)
        c = scheduler.schedule_day(p, case["n_hands"])
        checked = checker.check_day(p, c) if c["status"] == "FEASIBLE" else None
        tests = {"supported": p["status"] == "SUPPORTED", "no_input_mutation": scheduler.canonical_sha(p) == p_before,
                 "all_artificial_assets_included": len(p["start_farm_tiles"]) == len(case["tiles"]),
                 "generated_feasible": c["status"] == "FEASIBLE", "independent_checker_valid": checked is not None and checked["valid"]}
        if calendars:
            duplicated = compiler.compile_day_problem(calendars + [deepcopy(calendars[0])], **kwargs)
            tests["duplicate_calendar_unsupported"] = duplicated["status"] == "UNSUPPORTED" and "DUPLICATE_ASSET_CALENDAR" in duplicated["unsupported_reasons"]
        current = compiler.compile_day_problem(calendars, **(kwargs | {"current_day": day}))
        tests["current_day_legacy"] = current["status"] == "UNSUPPORTED" and "CURRENT_DAY_LEGACY" in current["unsupported_reasons"]
        startup = compiler.compile_day_problem(calendars, **kwargs, startup_fallback_days=[day])
        tests["unknown_startup_unsupported"] = startup["status"] == "UNSUPPORTED" and "UNSUPPORTED_STARTUP_FRONTIER" in startup["unsupported_reasons"]
        results.append({"id": case["id"], "tests": tests, "problem": p, "certificate": c, "checker": checked})
        failures.extend({"id": case["id"], "test": k} for k, v in tests.items() if not v)
    changed = [str(p) for p in paths if source[str(p)] != hashlib.sha256(p.read_bytes()).hexdigest()]
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "scope": "PURE PREPARATION ONLY",
              "complete_candidate_calls": 0, "official_environment_initializations": 0, "official_engine_steps": 0,
              "new_complete_matches": 0, "source_sha256": source, "source_changed": changed,
              "tests_passed": sum(sum(r["tests"].values()) for r in results), "tests_total": sum(len(r["tests"]) for r in results),
              "failures": failures, "cases": results}
    path = HERE / ("official_fixture_preparation_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"path": str(path), "passed": result["tests_passed"], "total": result["tests_total"], "failures": failures, "changed": changed}, ensure_ascii=False))
    return int(bool(failures or changed))


if __name__ == "__main__":
    raise SystemExit(main())
