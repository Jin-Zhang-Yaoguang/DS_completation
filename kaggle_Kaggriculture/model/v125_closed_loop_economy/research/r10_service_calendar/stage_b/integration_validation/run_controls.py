"""等待根放行的集成控制；必须绑定新prototype和全部输入freeze才可执行。"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time
import traceback
import types

HERE = Path(__file__).resolve().parent
MODEL = next(p for p in HERE.parents if p.name == "v125_closed_loop_economy")
PASS = {"farmer": ["PASS"], "hands": [], "market": []}
SCORE_KEYS = ("fixed_cash", "gross_cash_model", "net_before_hiring_model", "score_before_hiring", "net_cash_model", "cash_reserved_model", "feed_cash_model", "feed_cost_model", "hire_cash_model", "score", "selection_score", "labor")


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(value):
    if isinstance(value, dict):
        return {(str(k) if not isinstance(k, tuple) else "@tuple:" + json.dumps(k)): normalize(v) for k, v in value.items()}
    if isinstance(value, set): return {"__set__": sorted((normalize(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True))}
    if isinstance(value, (list, tuple)): return [normalize(v) for v in value]
    return value


def code_children(code):
    result = [code]
    for v in code.co_consts:
        if isinstance(v, types.CodeType): result.extend(code_children(v))
    return result


class CallDeadline(Exception): pass


def timed_call(fn, args, seconds):
    def expired(signum, frame): raise CallDeadline("人工工程单次保护超时" + str(seconds) + "秒")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    start = time.perf_counter()
    try: return fn(*args), time.perf_counter() - start
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, previous)


class BudgetProfile:
    """只按本次独立命名空间的精确code对象观测，不改frame或返回。"""
    def __init__(self, ns):
        outer = [ns["economic_plan_prefix"]]
        if "_r10_integration_legacy_economic_plan_prefix" in ns: outer.append(ns["_r10_integration_legacy_economic_plan_prefix"])
        self.budget_codes = {c for fn in outer for c in code_children(fn.__code__) if c.co_name == "budget_quote"}
        self.route_code = ns.get("_r10_integration_try_route").__code__ if ns.get("_r10_integration_try_route") else None
        self.prefix_code = ns["prefix_admission"].__code__
        self.funding_code = ns["funding_cash_book"].__code__
        self.budgets, self.routes, self.prefixes, self.live, self.route_live = [], [], [], {}, {}
        self.previous = None

    def __enter__(self): self.previous = sys.getprofile(); sys.setprofile(self.callback); return self
    def __exit__(self, *args): sys.setprofile(self.previous)

    def callback(self, frame, event, arg):
        code, loc = frame.f_code, frame.f_locals
        if code in self.budget_codes:
            if event == "call": self.live[id(frame)] = {"prefix_calls": 0, "funding_calls": 0}
            if event == "return":
                calls = self.live.pop(id(frame), {"prefix_calls": 0, "funding_calls": 0})
                returned_q, reason = arg if isinstance(arg, tuple) and len(arg) == 2 else (None, "EXCEPTION_OR_NON_TUPLE")
                q = loc.get("q")
                parent = frame.f_back.f_locals
                row = {"item": loc.get("item"), "position": list(loc.get("pos", [])),
                       "phase": "admission_recheck" if "q0" in parent else "initial_offer", "reason": reason,
                       "returned_quote_present": returned_q is not None, "local_quote_present": q is not None, **calls,
                       "quote_scores": {k: q.get(k) for k in SCORE_KEYS} if q else None,
                       "labor": deepcopy(loc.get("labor")), "workload": dict(loc.get("next_work", {})),
                       "actual_cash": parent.get("f", {}).get("money"),
                       "route_proof": deepcopy(q.get("_r10_approval")) if q else None,
                       "funding_admission": q.get("funding_admission") if q else None}
                self.budgets.append(row)
        elif code == self.route_code:
            if event == "call":
                self.route_live[id(frame)] = {"labor": deepcopy(loc["labor"]), "base_labor": deepcopy(loc["base_labor"]),
                    "workload": dict(loc["workload"]), "next_work": dict(loc["next_work"]),
                    "scores": {k: loc["q"].get(k) for k in SCORE_KEYS}}
            if event == "return":
                before = self.route_live.pop(id(frame))
                today = loc["ctx"]["obs"]["day"]; labor = loc["labor"]; next_work = loc["next_work"]
                old_failed = [d for d, need in next_work.items() if need > labor["capacity_by_day"][d]]
                proof = deepcopy(loc["q"].get("_r10_approval"))
                witnesses = proof.get("witnesses", []) if proof else []
                self.routes.append({"item": loc["q"]["item"], "position": list(loc["q"]["position"]), "today": today,
                    "result": arg, "old_failed_days": old_failed, "before": before, "proof": proof,
                    "invariants": {"old_labor_unchanged": before["labor"] == labor,
                        "base_labor_unchanged": before["base_labor"] == loc["base_labor"],
                        "work_unchanged": before["workload"] == dict(loc["workload"]) and before["next_work"] == dict(next_work),
                        "all_scores_unchanged": before["scores"] == {k: loc["q"].get(k) for k in SCORE_KEYS},
                        "only_original_future_failure": bool(old_failed) and all(d > today for d in old_failed),
                        "every_witness_is_original_future_failure": all(w["day"] > today and w["old_need"] > w["old_capacity"] for w in witnesses),
                        "every_override_future_failure": all(int(d) in old_failed and int(d) > today for d in (proof.get("route_feasibility_by_day", {}) if proof else {}))}})
        elif code == self.prefix_code and event == "return":
            parent = frame.f_back
            if parent.f_code in self.budget_codes and id(parent) in self.live: self.live[id(parent)]["prefix_calls"] += 1
            self.prefixes.append({"admission": arg, "original_new_cash": loc.get("original_new_cash"),
                                  "baseline": deepcopy(loc.get("baseline")), "trial": deepcopy(loc.get("trial"))})
        elif code == self.funding_code and event == "return":
            parent = frame.f_back
            if parent.f_code in self.budget_codes and id(parent) in self.live: self.live[id(parent)]["funding_calls"] += 1


class Controls:
    def __init__(self, out, freeze):
        self.out, self.freeze, self.counts, self.results, self.active = out, freeze, Counter(), [], None
        spec = importlib.util.spec_from_file_location("frozen_b_atom_observer", HERE.parent / "test_official_controls.py")
        self.base = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.base)
        self.rules = importlib.import_module("kaggle_environments.envs.kaggriculture.kaggriculture")
        self.make = importlib.import_module("kaggle_environments").make

    def save(self):
        if self.active is None: return
        path = self.out / (self.active["id"] + ".json.gz")
        with gzip.open(path, "wt") as f: json.dump(normalize(self.active), f, ensure_ascii=False, allow_nan=False)
        self.results.append({"id": self.active["id"], "path": str(path), "sha256": sha(path),
                             "checks": self.active.get("checks", {}), "diagnostic": self.active.get("diagnostic")})
        self.active = None

    def check(self, name, ok, detail=None):
        self.active.setdefault("checks", {})[name] = bool(ok)
        if not ok:
            self.active["first_failure"] = {"check": name, "detail": normalize(detail)}
            raise AssertionError(self.active["id"] + ":" + name)

    def namespace(self, kind, mode=None):
        path = Path(self.freeze["prototype_path"] if kind == "R10" else self.freeze["r9_path"])
        ns = {"__name__": "__r10_engineering_" + str(self.counts["module_definition_loads"]), "__file__": str(path)}
        self.counts["module_definition_loads"] += 1
        exec(compile(path.read_bytes(), str(path), "exec"), ns)
        self.check("fresh_module_state_" + str(self.counts["module_definition_loads"]), ns["_STATES"] == {})
        self.check("original_cash_prefix_" + str(self.counts["module_definition_loads"]), ns["PARAMS"]["cash_funding"] == "cash_prefix")
        if mode is not None: ns["PARAMS"]["r10_route_mode"] = mode
        # 仅为实际工程调用选入口，不重复独立的raw loader定义测试。
        entry = [v for v in ns.values() if callable(v)][-1]
        self.check("actual_loader_entry_agent_" + str(self.counts["module_definition_loads"]), entry is ns["agent"])
        self.active.setdefault("module_loads", []).append({"kind": kind, "mode_override": mode, "path": str(path), "sha256": sha(path),
            "entry_name": entry.__name__, "entry_line": entry.__code__.co_firstlineno, "entry_is_last_callable": True, "params": deepcopy(ns["PARAMS"])})
        return ns, entry

    def environment(self, initial):
        old = self.rules._initialize
        def init(*args, **kw): self.counts["official_initialize_helper_calls"] += 1; return old(*args, **kw)
        self.rules._initialize = init
        try:
            self.counts["official_make_calls"] += 1
            env = self.make("kaggriculture", configuration={"seed": 1250501, "episodeSteps": 720}, debug=False)
            self.counts["official_explicit_resets"] += 1; env.reset(2)
        finally: self.rules._initialize = old
        self.check("actual_agent_visible_configuration", dict(env.configuration) == self.freeze["agent_visible_configuration"], dict(env.configuration))
        shared = deepcopy(initial["farms"])
        for seat, state in enumerate(env.state):
            o = state.observation
            o.farms, o.market, o.town = shared, deepcopy(initial["market"]), deepcopy(initial["town"])
            o.step, o.day, o.hour, o.player = initial["step"], initial["day"], initial["hour"], seat
            o.remainingOverageTime = initial["remainingOverageTime"]
            o.private = deepcopy(initial["private"]) if seat == initial["player"] else {"shed": {}, "seeds": {}, "inventories": [{}]}
            state.status, state.reward = "ACTIVE", 0
        self.check("restored_initial_observation", self.observed(env, initial["player"]) == initial)
        return env

    def observed(self, env, seat): return deepcopy(dict(env.state[seat].observation))

    def agent(self, kind, entry, obs):
        self.counts[kind + "_complete_agent_calls"] += 1
        cfg = deepcopy(self.freeze["agent_visible_configuration"])
        self.check("seed_not_exposed", cfg.get("seed") is None and "seed" not in obs)
        start = time.perf_counter(); rec = {"kind": kind, "step": obs["step"], "profile": False}
        self.active.setdefault("call_times", []).append(rec)
        try:
            action, elapsed = timed_call(entry, (deepcopy(obs), cfg), 10)
            rec.update(seconds=elapsed, over_1s=elapsed > 1, returned_action=deepcopy(action))
        except BaseException as exc:
            elapsed = time.perf_counter() - start
            rec.update(seconds=elapsed, over_1s=elapsed > 1, exception={"type": type(exc).__name__, "message": str(exc)})
            raise
        self.check("agent_latency_le1s_call" + str(len(self.active["call_times"])), elapsed <= 1, elapsed)
        self.check("official_action_structure_call" + str(len(self.active["call_times"])), isinstance(action, dict) and isinstance(action.get("farmer"), list) and isinstance(action.get("hands"), list) and isinstance(action.get("market"), list) and len(action["market"]) <= 10, action)
        return deepcopy(action)

    def step(self, env, seat, action):
        old_step = env.state[0].observation.step
        pair = [deepcopy(PASS), deepcopy(PASS)]; pair[seat] = deepcopy(action)
        for state, act in zip(env.state, pair): state.action = act
        self.counts["official_short_steps"] += 1
        env.state = self.rules.interpreter(env.state, env)
        for state in env.state: state.observation.step = old_step + 1

    def legacy(self, case):
        self.active = {"id": "legacy_" + case["id"], "fixture": case, "rows": [], "checks": {}}
        ns0, entry0 = self.namespace("R9"); ns1, entry1 = self.namespace("R10", "legacy")
        e0, e1 = self.environment(case["observation"]), self.environment(case["observation"])
        seat = case["seat"]
        for _ in range(case["decision_count"]):
            o0, o1 = self.observed(e0, seat), self.observed(e1, seat)
            self.check("same_input_step" + str(o0["step"]), o0 == o1)
            a0, a1 = self.agent("R9", entry0, o0), self.agent("R10_legacy", entry1, o1)
            row = {"step": o0["step"], "input": o0, "R9_dispatched": a0, "R10_legacy_dispatched": a1}; self.active["rows"].append(row)
            self.check("same_action_step" + str(o0["step"]), a0 == a1, row)
            self.step(e0, seat, a0); self.step(e1, seat, a1)
            row.update(R9_after=self.observed(e0, seat), R10_legacy_after=self.observed(e1, seat))
            self.check("same_official_after_step" + str(o0["step"]), row["R9_after"] == row["R10_legacy_after"])
        self.active["R9_diagnostics"], self.active["R10_legacy_diagnostics"] = ns0["diagnostics"](), ns1["diagnostics"]()
        self.save()

    def executor(self, case):
        self.active = {"id": case["id"], "fixture": case, "rows": [], "checks": {}}
        ns, entry = self.namespace("R9")
        env, seat = self.environment(case["observation"]), case["seat"]
        obs = self.base.Observer(self.rules, env, seat)
        with obs:
            try:
                for _ in range(24):
                    before = self.observed(env, seat); action = self.agent("R9", entry, before)
                    self.step(env, seat, action)
                    self.active["rows"].append({"step": before["step"], "action": action, "after": self.observed(env, seat)})
            finally:
                self.active.update(unit_events=obs.unit_events, market_events=obs.market_events, hires=obs.hire_events, eod=obs.eod_events,
                                   final=self.observed(env, seat), diagnostics=ns["diagnostics"]())
        originals = {tuple(r["pos"]): r for r in case["original_assets"]}
        lots, harvested, placed, harvest_receipts, place_receipts, uncertain_transfers = {}, Counter(), Counter(), [], [], []
        for e in obs.unit_events:
            u, op = e["unit"], e["action"][0]
            lots.setdefault(u, [])
            if op == "HARVEST" and e["inventory_delta"].get("STRAWBERRY", 0) > 0:
                pos, tile = tuple(e["before"]["position"]), e["before"]["tile"]
                if pos in originals and isinstance(tile, dict) and tile.get("crop") == "STRAWBERRY" and tile.get("planted_day") == originals[pos]["tile"]["planted_day"]:
                    asset = originals[pos]["asset_id"]; n = e["inventory_delta"]["STRAWBERRY"]
                    harvested[asset] += n; lots[u].append([asset, n])
                    harvest_receipts.append({"asset_id": asset, "step": e["step"], "unit": u, "quantity": n})
            if op == "PLACE" and len(e["action"]) > 1 and e["action"][1] == "STRAWBERRY":
                left = e["shed_delta"].get("STRAWBERRY", 0)
                for lot in lots[u]:
                    take = min(left, lot[1]); left -= take; lot[1] -= take
                    if take:
                        placed[lot[0]] += take; place_receipts.append({"asset_id": lot[0], "step": e["step"], "unit": u, "quantity": take})
            delta = e["inventory_delta"].get("STRAWBERRY", 0)
            expected_transfer = op == "HARVEST" and delta >= 0 or op == "PLACE" and len(e["action"]) > 1 and e["action"][1] == "STRAWBERRY" and delta <= 0
            if delta and not expected_transfer:
                uncertain_transfers.append({"step": e["step"], "unit": u, "action": e["action"], "delta": delta})
                # 未表征的转移/损失使该执行者后续个体归因失效，不把旧lot留给后来PLACE。
                lots[u] = []
        sales = [m for m in obs.market_events if m["actual_commit"] and m["op"] == "SELL" and m["item"] == "STRAWBERRY"]
        external_strawberry = any(m["actual_commit"] and m["op"] == "BUY_PRODUCT" and m["item"] == "STRAWBERRY" for m in obs.market_events)
        untracked_harvest = sum(e["inventory_delta"].get("STRAWBERRY", 0) for e in obs.unit_events if e["action"][0] == "HARVEST") != sum(harvested.values())
        missing_harvest = [r["asset_id"] for r in case["original_assets"] if harvested[r["asset_id"]] < r["tile"]["yield_units"]]
        missing_place = [r["asset_id"] for r in case["original_assets"] if placed[r["asset_id"]] < r["tile"]["yield_units"]]
        self.active["diagnostic"] = {"original_asset_count": 48, "original_service_count": 96,
            "harvested_initial_asset_units": sum(harvested.values()), "explicit_placed_initial_asset_units": sum(placed.values()),
            "actual_sold_strawberry_units": len(sales), "actual_strawberry_sale_cash": sum(m["price"] for m in sales),
            "missing_harvest_assets": missing_harvest, "missing_explicit_place_assets": missing_place,
            "harvest_receipts": harvest_receipts, "explicit_place_receipts": place_receipts,
            "source_provenance_complete": not external_strawberry and not untracked_harvest and not uncertain_transfers,
            "uncertain_transfers": uncertain_transfers,
            "all_96_services_realized": not missing_harvest and not missing_place and not uncertain_transfers,
            "all_48_sold": len(sales) == 48 and not external_strawberry and not untracked_harvest and not uncertain_transfers,
            "eod_automatic_deposits": [e["automatic_deposit"] for e in obs.eod_events], "eod_discarded": [e["discarded"] for e in obs.eod_events],
            "scope": "工程诊断：未完成即报告执行缺口，不关闭默认投资或替换保存证书动作；EOD转仓不算PLACE。"}
        self.save()

    def default_pressure(self, case):
        self.active = {"id": "default_agent_" + case["id"], "fixture": case, "rows": [], "checks": {}}
        ns, entry = self.namespace("R10")
        self.check("default_mode_unchanged", ns["PARAMS"]["r10_route_mode"] == "future_failure_certificate")
        env, seat = self.environment(case["observation"]), case["seat"]
        before = self.observed(env, seat)
        observer = self.base.Observer(self.rules, env, seat)
        try:
            action = self.agent("R10_default", entry, before)
            with observer:
                self.step(env, seat, action)
            self.active["rows"].append({"step": before["step"], "action": action, "after": self.observed(env, seat)})
        finally:
            self.active.update(unit_events=observer.unit_events, market_events=observer.market_events, hires=observer.hire_events,
                final=self.observed(env, seat), diagnostics=ns["diagnostics"]())
        self.save()

    def pressure(self, case):
        self.active = {"id": "pressure_" + case["id"], "fixture": case, "modes": [], "checks": {}}
        for mode in ("legacy", "future_failure_certificate"):
            ns, _ = self.namespace("R10", mode)
            obs = deepcopy(case["observation"])
            self.counts["candidate_new_state_calls"] += 1; st = ns["new_state"](obs)
            self.counts["R10_economic_plan_prefix_calls"] += 1
            prof = BudgetProfile(ns)
            record = {"mode": mode, "budget_returns": prof.budgets, "route_returns": prof.routes, "actual_prefix_admission_calls": prof.prefixes}
            self.active["modes"].append(record)
            start = time.perf_counter()
            try:
                with prof: plan, elapsed = timed_call(ns["economic_plan_prefix"], (deepcopy(obs), st), 30)
            finally:
                record["seconds_profiled_not_performance_evidence"] = time.perf_counter() - start
                record["state_after"] = deepcopy(st)
            receipt = st["investment_receipts"][-1]
            record.update(plan=plan, receipt=receipt)
            for index, r in enumerate(prof.routes):
                for key, ok in r["invariants"].items(): self.check(mode + "_route" + str(index) + "_" + key, ok, r)
            if mode == "legacy": self.check("legacy_never_attempts_route", not prof.routes)
            else:
                audit = receipt["r10_future_route"]
                self.check("route_counter_matches_real_calls", audit["counts"].get("route_attempts", 0) == len(prof.routes))
                successful = [r for r in prof.budgets if r["route_proof"] and r["route_proof"]["labor_feasible_after_routes"]]
                self.check("every_route_pass_still_checks_cash", all(r["prefix_calls"] == 1 for r in successful), successful[:3])
                record["diagnostic"] = {"route_attempts": len(prof.routes), "successful_route_quotes": len(successful),
                    "successful_route_then_cash_rejection": sum(r["reason"] == "cash_prefix" for r in successful),
                    "actual_prefix_admission_calls": len(prof.prefixes), "probe_status": "TRIGGERED" if successful else "PENDING_NO_ROUTE_SUCCESS",
                    "last_accepted_proof": audit.get("last_accepted_proof")}
        old, new = self.active["modes"]
        key = lambda q: (q["item"], tuple(q["position"]))
        a = {key(q): q for q in old["budget_returns"] if q["phase"] == "initial_offer"}
        b = {key(q): q for q in new["budget_returns"] if q["phase"] == "initial_offer"}
        self.check("same_initial_quote_set", set(a) == set(b))
        self.check("initial_quote_cost_capacity_scores_exact", all(a[k]["quote_scores"] == b[k]["quote_scores"] and a[k]["labor"] == b[k]["labor"] and a[k]["workload"] == b[k]["workload"] for k in a))
        self.active["diagnostic"] = new["diagnostic"]
        self.save()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--freeze", required=True, type=Path); ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    raw = args.freeze.read_bytes(); freeze = json.loads(raw)
    if freeze.get("schema") != "r10-integration-execution-freeze-v1" or freeze.get("root_execution_release") is not True:
        raise SystemExit("root execution release missing")
    if args.output.exists(): raise SystemExit("REFUSE_EXISTING_OUTPUT")
    for p, value in freeze["files"].items():
        if sha(p) != value: raise SystemExit("SOURCE_SHA_MISMATCH:" + p)
    if sha(__file__) != freeze["files"].get(str(Path(__file__).resolve())): raise SystemExit("HARNESS_NOT_FROZEN")
    fixtures = json.loads(Path(freeze["fixtures_path"]).read_bytes())
    executors = json.loads(Path(freeze["executor_fixtures_path"]).read_bytes())
    args.output.mkdir(parents=True)
    suite, failure, case_failures = None, None, []
    try:
        suite = Controls(args.output, freeze)
        jobs = [(suite.legacy, c) for c in fixtures["cases"] if c["role"] == "legacy_equivalence"]
        jobs += [(suite.executor, c) for c in executors["cases"]]
        jobs += [(suite.default_pressure, c) for c in fixtures["cases"] if c["role"] == "future_route_integration" and c["manual_conditions"]["cash"] == 100000]
        jobs += [(suite.pressure, c) for c in fixtures["cases"] if c["role"] == "future_route_integration"]
        for fn, case in jobs:
            for p, value in freeze["files"].items():
                if sha(p) != value: raise ValueError("SOURCE_DRIFT_BEFORE_CASE:" + p)
            try: fn(case)
            except BaseException as exc:
                item = {"id": suite.active["id"] if suite.active else case["id"], "type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
                case_failures.append(item)
                if suite.active is not None: suite.active["run_error"] = item
                suite.save()
                if isinstance(exc, KeyboardInterrupt): raise
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        if suite: suite.save()
        drift = [p for p, value in freeze["files"].items() if sha(p) != value]
        if args.freeze.read_bytes() != raw: drift.append(str(args.freeze))
        counts = dict(suite.counts) if suite else {}; counts["new_complete_matches"] = 0
        result = {"schema": "r10-integration-controls-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
                  "status": "ERROR" if failure or drift or case_failures else "COMPLETE_ENGINEERING_DIAGNOSTIC", "failure": failure, "case_failures": case_failures, "source_drift": drift,
                  "counts": counts, "records": suite.results if suite else [], "freeze_sha256": hashlib.sha256(raw).hexdigest(),
                  "scope": "人工集成短控制；功能触发/执行兑现结果看diagnostic，不以工程运行结束宣告G1/G2/金牌。"}
        (args.output / "summary.json").write_text(json.dumps(normalize(result), ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print(json.dumps({k: result[k] for k in ("status", "counts", "failure", "case_failures", "source_drift")}, ensure_ascii=False))
    return int(bool(failure or drift or case_failures))


if __name__ == "__main__": raise SystemExit(main())
