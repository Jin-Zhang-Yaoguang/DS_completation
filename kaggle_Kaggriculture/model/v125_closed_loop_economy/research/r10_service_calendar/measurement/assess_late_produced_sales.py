"""R10 只读主机制原型：day11..29 实际自产非麦销售，含肥料。

完整入口必须先锁 tool_freeze.json 和开发 bundle；导入/纯算不读取比赛。
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
MODEL = next(p for p in HERE.parents if p.name == "v125_closed_loop_economy")
VERSIONS = ("V125-R9", "V125-R10")
OPPONENTS = ("PASS", "V120")
SEEDS = (1950906001, 1950906002, 1950906003)
START, END = 264, 718
PRODUCTS = ("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
EXPECTED = {(v, o, s, t) for v in VERSIONS for o in OPPONENTS for s in SEEDS for t in (0, 1)}
SHA = {"assessor": "02c3041d3c3e34e7d5c9d2cf712e01522e70b563912b72b7d6444ef0e5737f0c",
       "first_sale": "d353bd04bb4f86f492295a6d197389227934db87ff98414302538a04131a9c67",
       "G1": "fe4ebdfebd652a93e0847d5330355f1280a5fcf91db4239f65bc57734dcf2399",
       "analyzer": "cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def serialize(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def integer(value):
    return type(value) is int and value >= 0


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def window_sales(own, events, seat, origin_module):
    """原型的纯数值核。正式入口另须 first_sale.audit 和完整 source bundle。"""
    issues = []
    if type(seat) is not int or seat not in (0, 1):
        issues.append("INVALID_CANDIDATE_SEAT")
    for index, event in enumerate(events):
        step = event.get("decision_step")
        if type(event.get("seat")) is not int or event["seat"] not in (0, 1):
            issues.append("INVALID_EVENT_SEAT:" + str(index))
        if type(step) is not int or not 0 <= step <= 718:
            issues.append("INVALID_EVENT_STEP:" + str(index)); continue
        if type(event.get("recorded_step")) is not int or event["recorded_step"] != step + 1:
            issues.append("INVALID_RECORDED_STEP:" + str(index))
        if type(event.get("day")) is not int or event["day"] != step // 24 or type(event.get("hour")) is not int or event["hour"] != step % 24:
            issues.append("INCONSISTENT_EVENT_CLOCK:" + str(index))
    own_events = [e for e in events if type(e.get("seat")) is int and e["seat"] == seat]
    origin = origin_module.calculate(own, own_events)
    if origin.get("status") != "NUMERIC_COMPLETE":
        issues.extend("ORIGIN:" + x for x in origin.get("issues", ["PENDING"]))
    selected = []
    for index, event in enumerate(events):
        if type(event.get("seat")) is not int or event["seat"] != seat:
            continue
        step = event.get("decision_step")
        if type(step) is not int or not START <= step <= END or event.get("kind") != "market" or event.get("op") != "SELL" or event.get("item") not in PRODUCTS:
            continue
        qty, price = event.get("quantity"), event.get("price")
        if not integer(qty) or qty == 0 or not integer(price):
            issues.append("INVALID_OFFICIAL_INTEGER_SALE:" + str(index)); continue
        selected.append({"source_event_index": index, "decision_step": step, "recorded_step": step + 1,
                         "day": step // 24, "item": event["item"], "quantity": qty, "price": price, "cash": qty * price})
    if issues:
        return {"status": "PENDING_PROVENANCE", "issues": sorted(set(issues)), "window_decisions": [START, END],
                "cash": None, "units": None, "by_item": None, "daily": None, "sale_receipts": None,
                "origin_status": origin.get("status"), "no_qualifying_sale": None}
    by_item, daily = {}, {str(day): {"cash": 0, "units": 0} for day in range(11, 30)}
    for sale in selected:
        item = by_item.setdefault(sale["item"], {"cash": 0, "units": 0})
        item["cash"] += sale["cash"]; item["units"] += sale["quantity"]
        day = daily[str(sale["day"])]; day["cash"] += sale["cash"]; day["units"] += sale["quantity"]
    return {"status": "NUMERIC_COMPLETE", "issues": [], "window_decisions": [START, END],
            "cash": sum(x["cash"] for x in selected), "units": sum(x["quantity"] for x in selected),
            "by_item": by_item, "daily": daily, "sale_receipts": selected, "origin_status": origin["status"],
            "no_qualifying_sale": not selected,
            "definition": "day11h0..day29h22 实际官方 SELL 非WHEAT（含FERTILIZER）；全季非麦零初始/零外购且完整物量闭合。"}


def assess(rows):
    """固定24格、按对手 pooled cash，不用逐局均值或比例均值。"""
    issues, keys, sources = [], [], []
    for index, row in enumerate(rows):
        key = tuple(row.get(k) for k in ("candidate_id", "opponent", "seed", "seat"))
        keys.append(key); sources.append(row.get("source_key"))
        if type(key[2]) is not int or type(key[3]) is not int or key not in EXPECTED:
            issues.append("UNPLANNED_OR_INVALID_CELL:" + str(index))
        value = row.get("window", {})
        if value.get("status") != "NUMERIC_COMPLETE" or value.get("window_decisions") != [START, END]:
            issues.append("PENDING_OR_WRONG_WINDOW:" + str(index))
        if not integer(value.get("cash")) or not integer(value.get("units")):
            issues.append("INVALID_CASH_OR_UNITS:" + str(index))
    counts = Counter(keys)
    if set(counts) != EXPECTED or any(n != 1 for n in counts.values()):
        issues.append("MISSING_DUPLICATE_OR_UNPLANNED_CELL")
    if any(not isinstance(k, str) or not k for k in sources) or len(set(sources)) != len(sources):
        issues.append("MISSING_OR_DUPLICATE_SOURCE_GAME_KEY")
    valid, groups = not issues, []
    for opponent in OPPONENTS:
        rr = {v: [r for r in rows if r.get("candidate_id") == v and r.get("opponent") == opponent] for v in VERSIONS}
        stats = {v: {"games": len(rr[v]), "cash_sum": sum(r["window"]["cash"] for r in rr[v]) if valid else None,
                     "units_sum": sum(r["window"]["units"] for r in rr[v]) if valid else None,
                     "zero_cash_games": sum(r.get("window", {}).get("cash") == 0 for r in rr[v])} for v in VERSIONS}
        per_seat = {}
        for seat in (0, 1):
            sums = {v: sum(r["window"]["cash"] for r in rr[v] if r["seat"] == seat) if valid else None for v in VERSIONS}
            sums["nondecline"] = sums["V125-R10"] >= sums["V125-R9"] if valid else None
            per_seat[str(seat)] = sums
        parent, child = stats["V125-R9"]["cash_sum"], stats["V125-R10"]["cash_sum"]
        numeric = valid and parent > 0
        threshold = 5 * child >= 6 * parent if numeric else None
        passed = threshold and all(s["nondecline"] for s in per_seat.values()) if numeric else None
        groups.append({"opponent": opponent, "status": "NUMERIC_COMPLETE" if numeric else "PENDING",
            "reason": None if numeric else "EVIDENCE_INVALID_OR_PARENT_SUM_ZERO", "stats": stats, "per_seat": per_seat,
            "relative_cash_change": child / parent - 1 if numeric else None, "at_least_20_percent": threshold,
            "primary_numeric_threshold_pass": passed})
    return {"issues": sorted(set(issues)), "data_integrity_pass": valid, "groups": groups,
            "expected_games": 24, "observed_rows": len(rows), "window_decisions": [START, END],
            "primary_mechanism_numeric_threshold_pass": all(g["primary_numeric_threshold_pass"] is True for g in groups),
            "rule": "每对手6局5×R10现金sum≥6×R9现金sum，每席3局sum不退；parent0/PENDING不通过。"}


class Inputs:
    def __init__(self): self.files = {}
    def raw(self, path, expected=None):
        path = str(Path(path).resolve()); raw = Path(path).read_bytes(); value = hashlib.sha256(raw).hexdigest()
        if expected is not None and value != expected: raise ValueError("SOURCE_SHA_MISMATCH:" + path)
        if path in self.files and self.files[path] != value: raise ValueError("SOURCE_CHANGED:" + path)
        self.files[path] = value
        return raw
    def read(self, path, expected=None): return json.loads(self.raw(path, expected))
    def pin(self, path, expected=None): self.raw(path, expected)
    def verify(self):
        for path, value in self.files.items():
            if sha(path) != value: raise ValueError("SOURCE_CHANGED_BEFORE_OUTPUT:" + path)


def evaluate_saved(args, inputs):
    ownsha = sha(__file__)
    inputs.pin(__file__, ownsha)
    freeze = inputs.read(HERE / "tool_freeze.json")
    if freeze["aggregator_sha256"] != ownsha: raise ValueError("UNFROZEN_AGGREGATOR")
    plan = inputs.read(args.plan)
    if not (plan["candidate"] == "V125-R10" and set(plan["references"]) == {"V125-R0", "V125-R9"}
            and plan["seeds"] == list(SEEDS) and all(type(x) is int for x in plan["seeds"] + plan["seats"])
            and plan["seats"] == [0, 1] and plan["opponents"] == list(OPPONENTS) and plan["expected_games"] == 36):
        raise ValueError("WRONG_REGISTERED_PLAN")
    for field in ("runner_sha256", "engine_composite_sha256", "formal_protocol_sha256", "development_protocol_sha256"):
        if plan[field] != freeze[field]: raise ValueError("PLAN_FREEZE_MISMATCH:" + field)
    inputs.pin(HERE.parent / "development_protocol.json", plan["development_protocol_sha256"])
    paths = {"assessor": MODEL / "evaluation/assess_paired_development.py",
             "first_sale": MODEL / "research/r8_terminal_net_selection/summarize_first_produced_sale_v3.py",
             "G1": MODEL / "evaluation/summarize_g1.py",
             "analyzer": MODEL / "research/mechanism_analysis/analyze_trace.py"}
    modules = {}
    for name, path in paths.items():
        inputs.pin(path, SHA[name])
        if name != "analyzer": modules[name] = load(path, "r10_readonly_" + name)
    sm = inputs.read(args.strength_dir / "assessment_manifest.json")
    strength = inputs.read(args.strength_dir / "assessment.json")
    if sm["assessor"]["sha256"] != SHA["assessor"] or sm["plan"]["sha256"] != inputs.files[str(args.plan.resolve())]:
        raise ValueError("STRENGTH_IDENTITY_MISMATCH")
    for path, value in sm["source_files"].items(): inputs.pin(path, value)
    sp, snapshots, errors, files = modules["assessor"].read_plan(args.plan.resolve())
    for path, value in files.items(): inputs.pin(path, value)
    if sp != plan or modules["assessor"].evaluate(sp, snapshots, errors) != strength:
        raise ValueError("STRENGTH_ASSESSMENT_NOT_REPRODUCIBLE")
    if strength["data_integrity_pass"] is not True or strength["observed_unique_cells"] != 36 or strength["expected_games"] != 36:
        raise ValueError("FULL36_ENGINEERING_INTEGRITY_NOT_PASSED")
    fm = inputs.read(args.first_sale_dir / "manifest.json")
    if fm["script_sha256"] != SHA["first_sale"]: raise ValueError("UNAPPROVED_FIRST_SALE")
    fs = inputs.read(args.first_sale_dir / "first_sale.json", fm["output_sha256"])
    for path, value in fm["input_files"].items(): inputs.pin(path, value)
    expected = {}
    for index, job in enumerate(plan["jobs"]):
        if job["candidate_id"] not in VERSIONS: continue
        for game in snapshots[index]["games"]:
            if game["key"] in expected: raise ValueError("DUPLICATE_SOURCE_GAME")
            expected[game["key"]] = job, snapshots[index]["manifest"], game
    if len(expected) != 24 or len(fs["games"]) != 24 or len({f["game_key"] for f in fs["games"]}) != 24 or {f["game_key"] for f in fs["games"]} != set(expected):
        raise ValueError("FIRST_SALE_NOT_EXACT24")
    rows = []
    for saved in fs["games"]:
        job, rm, game = expected[saved["game_key"]]
        auditdir = Path(saved["audit_directory"])
        verified, fingerprints = modules["first_sale"].audit(auditdir)
        for path, value in fingerprints.items(): inputs.pin(path, value)
        if serialize(verified) != saved: raise ValueError("FIRST_SALE_AUDIT_NOT_REPRODUCIBLE")
        if (saved["seed"], saved["seat"], saved["source_sha256"]) != (game["seed"], game["candidate_seat"], job["entry_sha256"]):
            raise ValueError("FIRST_SALE_GAME_IDENTITY_MISMATCH")
        manifest = inputs.read(auditdir / "audit_manifest.json")
        if Path(manifest["source_run_manifest"]["path"]).resolve() != (Path(job["output"]) / "run_manifest.json").resolve():
            raise ValueError("AUDIT_RUN_IDENTITY_MISMATCH")
        if manifest["candidate_entry_sha256"] != job["entry_sha256"] or manifest["engine_composite_sha256"] != plan["engine_composite_sha256"]:
            raise ValueError("AUDIT_ENGINE_OR_ENTRY_SHA_MISMATCH")
        if rm["configuration"].get("turnsPerDay", 24) != 24: raise ValueError("WRONG_CLOCK_CONFIGURATION")
        analysis = inputs.read(auditdir / "analysis.json")
        events = [json.loads(line) for line in gzip.decompress(inputs.raw(auditdir / "events.jsonl.gz")).decode().splitlines()]
        own = analysis["seats"][game["candidate_seat"]]
        metric = window_sales(own, events, game["candidate_seat"], modules["first_sale"])
        # G1只保留原冻结数值诊断，不在本开发测量器做正式资格裁决。
        g1 = modules["G1"].game_metrics(game, rm, Path(job["output"]), auditdir)
        rows.append({"candidate_id": job["candidate_id"], "opponent": job["opponent_label"], "seed": game["seed"],
                     "seat": game["candidate_seat"], "source_key": game["key"], "window": metric, "G1_numeric_companions": g1,
                     "first_sale": saved, "actual_flow": own["actual_flow"], "denominators": own["denominators"],
                     "overflow": own["overflow"], "terminal_assets": own["terminal_assets"],
                     "own_cash": game["candidate_reward"], "opponent_cash": game["opponent_reward"], "margin": game["margin"]})
    report = assess(rows)
    report.update(schema="r10-late-self-produced-sales-v1", per_game=rows, candidate_calls=0, engine_steps=0, new_independent_matches=0,
                  formal_G1_G2_Gold="NOT_ASSESSED", development_strength_guard_pass=strength["development_strength_guard_pass"],
                  qualification="开发预筛主机制；通过不覆盖强度失败或任何正式门。")
    inputs.verify()
    return report


def main():
    parser = argparse.ArgumentParser()
    for name in ("plan", "first-sale-dir", "strength-dir", "output"): parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()): raise SystemExit("REFUSE_EXISTING_OUTPUT")
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = Inputs()
    try:
        result = evaluate_saved(args, inputs)
        inputs.verify()
        (args.output / "assessment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        manifest = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": sha(__file__), "sources": inputs.files,
                    "assessment_sha256": sha(args.output / "assessment.json"), "candidate_calls": 0, "engine_steps": 0, "new_independent_matches": 0}
        (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print(json.dumps({k: result[k] for k in ("data_integrity_pass", "groups", "primary_mechanism_numeric_threshold_pass", "development_strength_guard_pass")}, ensure_ascii=False))
    except BaseException as exc:
        failure = {"status": "PENDING", "data_integrity_pass": False, "primary_mechanism_numeric_threshold_pass": False,
                   "error": str(exc), "traceback": traceback.format_exc(), "candidate_calls": 0, "engine_steps": 0, "new_independent_matches": 0,
                   "sources_read_before_failure": inputs.files}
        (args.output / "failure.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        raise


if __name__ == "__main__":
    main()
