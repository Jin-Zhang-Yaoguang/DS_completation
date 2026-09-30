"""只执行预登记 48 草莓保存证书×双席；复用冻结逐原子官方核对。"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import traceback

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists")
    freeze_bytes = args.freeze.read_bytes()
    frozen = json.loads(freeze_bytes)
    if frozen.get("schema") != "r10-stage-b-pressure-official-freeze-v1":
        raise SystemExit("invalid freeze")
    for p, expected in frozen["files"].items():
        if sha(p) != expected:
            raise SystemExit("source drift " + p)
    source_bytes = Path(frozen["pressure_source"]).read_bytes()
    data = json.loads(source_bytes)
    rows = [r for r in data["rows"] if r["name"] == "48_strawberries"]
    if len(rows) != 1:
        raise SystemExit("selected fixture missing/duplicated")
    selected = rows[0]
    spec = importlib.util.spec_from_file_location("frozen_b_official_controls", HERE / "test_official_controls.py")
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    if base.canonical(selected["problem"]) != frozen["problem_sha256"] or base.canonical(selected["certificate"]) != frozen["certificate_sha256"]:
        raise SystemExit("problem/certificate changed")
    if selected["legacy_capacity"] != 298 or selected["problem"]["legacy_work"] != 366 or not selected["legacy_failed"]:
        raise SystemExit("wrong pressure premise")

    class PressureSuite(base.Suite):
        def run_saved(self, seat):
            self.start("48_strawberries_saved_certificate", seat, "saved_pressure_certificate_official_day")
            p, cert = deepcopy(selected["problem"]), deepcopy(selected["certificate"])
            self.active.update(problem=p, certificate=cert, source_checker=selected["checker"],
                source_pressure_name=selected["name"], legacy_work=366, legacy_capacity=298,
                assumption="人工四象限已解锁且土地费用已发生；100000现金；不证明自然到达/未来资金")
            self.counts["checker_calls"] += 1
            checked = self.checker.check_day(p, cert)
            self.active["checker"] = checked
            self.check("independent_saved_certificate_valid", checked["valid"], checked)
            self.check("saved_checker_reproducible", checked == selected["checker"])
            self.check("exact_problem_hash", base.canonical(p) == frozen["problem_sha256"])
            self.check("exact_certificate_hash", base.canonical(cert) == frozen["certificate_sha256"])
            self.check("all_48_assets_present", len(p["start_farm_tiles"]) == 48)
            # 只生成附加条件 next-day tile 作为对照；不重编 problem、不重调路线。
            calendars = []
            for row in p["start_farm_tiles"]:
                self.counts["calendar_calls"] += 1
                calendars.append(self.compiler.project_calendar_with_services(row["tile"], p["day"], 0, tuple(row["pos"]),
                    {"kind": "artificial_saved_pressure_state", "natural_reachability": "NOT_PROVEN"}))
            self.active["input_calendars"] = calendars
            env = self.env({"day": p["day"], "tiles": p["start_farm_tiles"], "shed": p["start_shed"]}, seat)
            farm = env.state[0].observation.farms[seat]
            # 所有空地可用与解锁元数据一致，土地成本为已发生初态条件。
            farm["unlocked_quadrants"] = ["NW", "NE", "SW", "SE"]
            farm["tiles"] = [[None for _ in range(10)] for _ in range(10)]
            for row in p["start_farm_tiles"]:
                x, y = row["pos"]; farm["tiles"][y][x] = deepcopy(row["tile"])
            self.active["initial"] = base.state_snapshot(env, seat)
            self.check("land_metadata_matches_injected_board", farm["unlocked_quadrants"] == ["NW", "NE", "SW", "SE"] and all(t != "LOCKED" for line in farm["tiles"] for t in line))
            by_hour = {h: {} for h in range(24)}
            for entry in cert["actions"]:
                by_hour[entry["hour"]][entry["unit"]] = entry
            markets = {m["hour"]: m["orders"] for m in cert["markets"]}
            obs = base.Observer(self.rules, env, seat)
            with obs:
                try:
                    for h in range(24):
                        units = by_hour[h]
                        f = env.state[0].observation.farms[seat]
                        self.check(f"actual_workers_h{h}", set(units) == set(range(len(f["hands"]) + 1)))
                        action = {"farmer": units[0]["action"], "hands": [units[u]["action"] for u in range(1, len(units))], "market": markets[h]}
                        self.step(env, seat, action)
                    self.verify_certificate(p, cert, checked, obs, env, seat)
                    self.check("saved_problem_unchanged_after_execution", base.canonical(p) == frozen["problem_sha256"])
                    self.check("saved_certificate_unchanged_after_execution", base.canonical(cert) == frozen["certificate_sha256"])
                finally:
                    self.attach(obs, env, seat)
            self.save()

    args.output.mkdir(parents=True)
    suite, failure = None, None
    try:
        suite = PressureSuite(args.output, frozen)
        for seat in (0, 1):
            suite.run_saved(seat)
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        if suite: suite.save()
        drift = [p for p, expected in frozen["files"].items() if sha(p) != expected]
        if args.freeze.read_bytes() != freeze_bytes: drift.append(str(args.freeze))
        if Path(frozen["pressure_source"]).read_bytes() != source_bytes: drift.append(frozen["pressure_source"])
        counts = dict(suite.counts) if suite else {}
        counts.update(complete_candidate_calls=0, new_complete_matches=0, scheduler_calls=0, compiler_calls=0)
        result = {"schema": "r10-stage-b-pressure-official-control-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ERROR" if failure or drift else "PASS", "failure": failure, "source_drift": drift,
            "counts": counts, "runs": suite.results if suite else [], "freeze_sha256": hashlib.sha256(freeze_bytes).hexdigest(),
            "source_files": frozen["files"], "problem_sha256": frozen["problem_sha256"], "certificate_sha256": frozen["certificate_sha256"],
            "legacy_work": 366, "legacy_capacity": 298, "scope": "仅48草莓双席保存证书人工官方控制；0新完整游戏/0完整候选；不重跑首轮。"}
        (args.output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print(json.dumps({k: result[k] for k in ("status", "counts", "failure", "source_drift")}, ensure_ascii=False))
    return int(bool(failure or drift))


if __name__ == "__main__":
    raise SystemExit(main())
