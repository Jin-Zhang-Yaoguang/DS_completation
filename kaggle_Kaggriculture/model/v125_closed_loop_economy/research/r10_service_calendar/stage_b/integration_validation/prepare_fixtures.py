"""只读旧人工初态、生成新人工压力输入；不导入策略或官方引擎。"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = next(p for p in HERE.parents if p.name == "v125_closed_loop_economy")
SOURCE = MODEL / "research/r9_cash_prefix/micro_e7f1fd549fc6_20260905T115709465395Z.json"
PRESSURE = HERE.parent / "pressure_fixtures_20260905T125348773917Z.json"
R9 = MODEL / "candidates/V125-R9/main.py"
EXPECTED_SHA = {SOURCE: "6f1747c309070c15af3dacd5b363772926d57a80276821a7aa917584da3ded6d",
                PRESSURE: "2fd7ca4ab2c4da52acdf7c751fa7dd185121cfeb15bd1f867d9dbc5e137aeda7",
                R9: "e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main():
    paths = [*EXPECTED_SHA, Path(__file__).resolve()]
    fingerprints = {str(p): sha(p) for p in paths}
    for p, expected in EXPECTED_SHA.items():
        if fingerprints[str(p)] != expected: raise ValueError("SOURCE_SHA_MISMATCH:" + str(p))
    data, pressure = json.loads(SOURCE.read_bytes()), json.loads(PRESSURE.read_bytes())
    oldrows = [r for r in data["runs"] if r["name"].endswith("_R9_full_reserve")]
    if len(oldrows) != 6 or {(r["name"], r["seat"]) for r in oldrows} != {(case + "_R9_full_reserve", seat) for case in ("initial", "care_crossday", "in_transit") for seat in (0, 1)}:
        raise ValueError("SOURCE_INITIAL_FIXTURES_NOT_EXACT_SIX")
    cases = []
    for r in oldrows:
        obs = deepcopy(r["initial_observation"])
        cases.append({"id": r["name"].removesuffix("_R9_full_reserve") + "_s" + str(r["seat"]), "role": "legacy_equivalence",
                      "seat": r["seat"], "decision_count": len(r["rows"]), "observation": obs,
                      "observation_sha256": canonical(obs), "source_row": {"name": r["name"], "seat": r["seat"]},
                      "source": str(SOURCE), "source_sha256": EXPECTED_SHA[SOURCE],
                      "reuse_scope": "只复用已保存人工初始观察和步数；不复用旧full_reserve动作。新基线R9保持默认prefix，R10仅r10_route_mode=legacy。",
                      "other_private_condition": "原记录仅有本席private；未来环境恢复时对手private显式为空，双路径完全相同。",
                      "natural_reachability": "NOT_PROVEN_ARTIFICIAL_LOCAL_STATE"})
    source_pressure = [r for r in pressure["rows"] if r["name"] == "48_strawberries"]
    if len(source_pressure) != 1: raise ValueError("PRESSURE_POSITION_SET_NOT_UNIQUE")
    positions = [r["pos"] for r in source_pressure[0]["problem"]["start_farm_tiles"]]
    if len(positions) != 48 or len({tuple(p) for p in positions}) != 48: raise ValueError("INVALID_PRESSURE_POSITIONS")
    for seat in (0, 1):
        initial = next(r["observation"] for r in cases if r["id"] == "initial_s" + str(seat))
        for label, cash in (("funded", 100000), ("zero_cash", 0)):
            obs = deepcopy(initial)
            obs.update(day=8, hour=0, step=192)
            farm = obs["farms"][seat]
            farm.update(money=cash, farmer=[4, 4], hands=[], hires_today=0, unlocked_quadrants=["NW", "NE", "SW", "SE"])
            farm["tiles"] = [[None for _ in range(10)] for _ in range(10)]
            for x, y in positions:
                farm["tiles"][y][x] = {"kind": "PLANT", "crop": "STRAWBERRY", "planted_day": 0,
                    "watered_today": True, "consecutive_unwatered": 0, "yield_units": 0,
                    "max_lifespan_step": -1, "fertilized_until_day": -1}
            obs["private"] = {"shed": {}, "seeds": {}, "inventories": [{}]}
            cases.append({"id": "48_strawberries_day8_" + label + "_s" + str(seat), "role": "future_route_integration",
                          "seat": seat, "decision_count": 1, "observation": obs, "observation_sha256": canonical(obs),
                          "source_position_set": str(PRESSURE), "source_position_set_sha256": EXPECTED_SHA[PRESSURE],
                          "manual_conditions": {"land": "四象限已解锁，土地支出已发生，不记入本次收益或授信",
                              "plants": "48已到位STRAWBERRY，day8已浇水、无当前成熟产物；过去存活历史只作人工条件",
                              "cash": cash, "inventories": "仓/种/包空", "workers": "农夫仓口；无雇工；hires_today0"},
                          "natural_reachability": "NOT_PROVEN_ARTIFICIAL_LOCAL_STATE",
                          "expected_scope": "检测未来劳动拒绝是否由证书解除；当前准入、原成本/容量/score保持；现金门必须实际执行。是否触发以捕获证据为准，不预填通过。"})
    checks = []
    for c in cases:
        obs, seat = c["observation"], c["seat"]
        checks.append({"id": c["id"], "clock_consistent": obs["step"] == obs["day"] * 24 + obs["hour"],
                       "seat_consistent": obs["player"] == seat, "observation_sha_consistent": canonical(obs) == c["observation_sha256"],
                       "no_new_seed": True})
        if c["role"] == "future_route_integration":
            f = obs["farms"][seat]; tiles = [t for row in f["tiles"] for t in row if isinstance(t, dict)]
            checks[-1].update(asset_count48=len(tiles) == 48, all_already_watered=all(t["watered_today"] for t in tiles),
                              consistent_unlocked_land=f["unlocked_quadrants"] == ["NW", "NE", "SW", "SE"] and all(t != "LOCKED" for row in f["tiles"] for t in row),
                              no_mature_stock=all(t["yield_units"] == 0 for t in tiles))
    if not all(all(v for k, v in c.items() if k != "id") for c in checks): raise ValueError("STATIC_FIXTURE_CHECK_FAILED")
    for path, value in fingerprints.items():
        if sha(Path(path)) != value: raise ValueError("SOURCE_CHANGED_DURING_PREPARATION")
    output = {"schema": "r10-integration-static-fixtures-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "STATIC_PREPARED_NOT_EXECUTED", "source_files": fingerprints, "cases": cases, "static_checks": checks,
              "configuration": {"seed_for_future_official_initialization": 1250501, "agent_visible_seed": None,
                                "episodeSteps": 720, "turnsPerDay": 24},
              "switch": {"R10_default": "future_failure_certificate", "R10_ablation": "legacy", "key": "PARAMS.r10_route_mode",
                         "R9_cash_funding": "original_default_prefix_unchanged"},
              "candidate_calls": 0, "engine_initializations": 0, "engine_steps": 0, "new_complete_matches": 0,
              "execution_authorized_by_this_file": False}
    p = HERE / "fixtures_v1.json"
    if p.exists(): raise ValueError("REFUSE_EXISTING_FIXTURES")
    p.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(p), "sha256": sha(p), "cases": len(cases), "candidate_calls": 0, "engine_steps": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
