"""只读日历反例；不导入候选或官方引擎，不改冻结核心。"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "calendar_compiler.py"
before = SOURCE.read_bytes()
sha = hashlib.sha256(before).hexdigest()
spec = importlib.util.spec_from_file_location("review_calendar_compiler", SOURCE)
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)
tile = {"kind": "PLANT", "crop": "WHEAT", "planted_day": 0,
        "yield_units": 1, "watered_today": False, "consecutive_unwatered": 1,
        "fertilized_until_day": -1, "max_lifespan_step": 120}
cal = compiler.project_calendar_with_services(deepcopy(tile), 0, 24, (4, 4),
        {"kind": "artificial_known_impossible_first_water_window"})
without_impossible_water = compiler._model_next_day(deepcopy(tile), 0)
future_problems = {}
for day in (1, 2):
    future_problems[day] = compiler.compile_day_problem(
        [cal], day, 0, {}, {},
        {"qty": 0, "estimated_cash": 0, "order_hour": 0, "available_from_hour": 1},
        cal["work"].get(day, 0), 0, startup_fallback_days=[0])
out = {
    "scope": "PURE_COMPILER_COUNTEREXAMPLE_NOT_OFFICIAL_OR_CANDIDATE_EXECUTION",
    "counts": {"project_calendar": 1, "pure_model_next_day": 1, "compile_day_problem": 2,
               "candidate_calls": 0, "official_calls": 0, "matches": 0},
    "compiler_sha256": sha,
    "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "input": {"tile": tile, "day": 0, "hour": 24, "pos": [4, 4]},
    "day0_services": cal["services"].get(0),
    "unsupported_by_day": cal["unsupported_by_day"],
    "predicted_day1_state": cal["state_by_day"][1],
    "same_model_next_day_without_impossible_water": without_impossible_water,
    "future_problems": future_problems,
    "finding": "Known-impossible day0 WATER is nevertheless applied to future state; later day compiles SUPPORTED despite startup fallback day0.",
    "source_unchanged": SOURCE.read_bytes() == before,
}
assert out["source_unchanged"]
assert cal["services"][0][0]["release"] > cal["services"][0][0]["deadline"]
assert cal["state_by_day"][1]["kind"] == "PLANT"
assert without_impossible_water == {"kind": "WEED"}
assert all(p["status"] == "SUPPORTED" for p in future_problems.values())
dest = HERE / ("review_impossible_history_probe_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"artifact": str(dest), "compiler_sha256": sha, "reproduced": True,
                  "source_unchanged": True, "candidate_calls": 0, "official_calls": 0}, ensure_ascii=False))
