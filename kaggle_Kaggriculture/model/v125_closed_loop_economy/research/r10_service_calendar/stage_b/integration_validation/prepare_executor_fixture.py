"""静态准备 R9 执行器双席对照；不导入策略/引擎。"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "pressure_fixtures_20260905T125348773917Z.json"
BASE = HERE / "fixtures_v1.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main():
    expected = {SOURCE: "2fd7ca4ab2c4da52acdf7c751fa7dd185121cfeb15bd1f867d9dbc5e137aeda7",
                BASE: "002242ff38a0d9e4feb489782ab8cbf17e159bdb20b00b5882b4186f5f1b0537"}
    for p, value in expected.items():
        if sha(p) != value: raise ValueError("SOURCE_SHA_MISMATCH:" + str(p))
    source, base = json.loads(SOURCE.read_bytes()), json.loads(BASE.read_bytes())
    rows = [r for r in source["rows"] if r["name"] == "48_strawberries"]
    if len(rows) != 1: raise ValueError("DUPLICATE_OR_MISSING_CASE")
    p, cert = rows[0]["problem"], rows[0]["certificate"]
    cases = []
    for seat in (0, 1):
        obs = deepcopy(next(c["observation"] for c in base["cases"] if c["id"] == "initial_s" + str(seat)))
        obs.update(day=10, hour=0, step=240)
        f = obs["farms"][seat]
        f.update(money=100000, farmer=[4, 4], hands=[], hires_today=0, unlocked_quadrants=["NW", "NE", "SW", "SE"])
        f["tiles"] = [[None for _ in range(10)] for _ in range(10)]
        for row in p["start_farm_tiles"]:
            x, y = row["pos"]; f["tiles"][y][x] = deepcopy(row["tile"])
        obs["private"] = {"shed": deepcopy(p["start_shed"]), "seeds": {}, "inventories": [{}]}
        cases.append({"id": "r9_executor_48_strawberries_day10_s" + str(seat), "seat": seat, "decision_count": 24,
                      "observation": obs, "observation_sha256": canonical(obs), "problem_sha256": canonical(p),
                      "certificate_sha256": canonical(cert), "original_service_ids": [s["service_id"] for s in p["services"]],
                      "original_assets": deepcopy(p["start_farm_tiles"]),
                      "candidate": "V125-R9", "candidate_sha256": "e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0",
                      "parameter_overrides": {}, "mode": "DEFAULT_COMPLETE_REAL_ENTRY",
                      "scope": "不执行证书动作，执行冻结R9真实入口输出；逐个初始资产核HARVEST及带来源的明确PLACE/实际SELL。",
                      "manual_conditions": "沿保存problem原48资产/仓存，人工四象限已解锁、土地支出已发生、现金100000；不证明自然可达。",
                      "execution_status": "NOT_EXECUTED"})
    for c in cases:
        obs, seat = c["observation"], c["seat"]
        assert obs["player"] == seat and obs["step"] == 240 and len(c["original_assets"]) == 48
        assert len(c["original_service_ids"]) == len(set(c["original_service_ids"])) == 96
        for row in p["start_farm_tiles"]:
            x, y = row["pos"]; assert obs["farms"][seat]["tiles"][y][x] == row["tile"]
    result = {"schema": "r10-integration-r9-executor-static-fixtures-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "STATIC_PREPARED_NOT_EXECUTED", "source_files": {str(p): sha(p) for p in [*expected, Path(__file__).resolve()]},
              "problem": p, "saved_certificate": cert, "cases": cases,
              "planned_r9_entry_calls": 48, "planned_official_short_steps": 48, "candidate_calls": 0, "engine_steps": 0,
              "new_complete_matches": 0, "execution_requires_root_release_after_source_freeze": True}
    out = HERE / "executor_fixtures_v1.json"
    if out.exists(): raise ValueError("REFUSE_EXISTING_OUTPUT")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(out), "sha256": sha(out), "cases": len(cases), "candidate_calls": 0, "engine_steps": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
