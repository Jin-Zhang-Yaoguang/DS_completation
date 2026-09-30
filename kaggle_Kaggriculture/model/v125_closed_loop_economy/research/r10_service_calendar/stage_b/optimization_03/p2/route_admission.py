"""R10 B 独立未来日劳动准入；不导入或调用候选，不改变原资金与评分。"""
from collections import Counter
from copy import deepcopy
import math

from calendar_compiler import canonical_sha, compile_day_problem

PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"}
ANIMALS = {"COW", "SHEEP", "GOOSE"}
IMPLEMENTATION_ID = "r10-route-admission-v1"
COMPACT_MODE = "production_compact_v1"
COMPACT_SCHEMA = "r10-production-evidence-summary-v1"


class BindingError(ValueError):
    pass


def _need(test, reason):
    if not test:
        raise BindingError(reason)


def _qty(value, name):
    _need(type(value) is int and value >= 0, name + ":INVALID_QUANTITY")
    return value


def _day_map(data, name, start, *, numeric=False):
    _need(isinstance(data, dict), name + ":MISSING_MAP")
    _need(set(data) == set(range(start, 30)), name + ":DAY_COVERAGE")
    for value in data.values():
        if numeric:
            _need(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                  name + ":INVALID_NUMBER")
        else:
            _qty(value, name)
    return data


def _normal_sparse(data):
    """只规范零项，不改变值；没有缺日填充粮账的功能。"""
    return {d: ({p: n for p, n in value.items() if n} if isinstance(value, dict) else value)
            for d, value in data.items() if value}


def aggregate_calendars(calendars):
    """从原字段聚合；服务字段另核，不由 work 反推。"""
    work, feed, goods = Counter(), Counter(), {}
    seen = set()
    for cal in calendars:
        aid = cal["asset_id"]
        _need(aid not in seen, "DUPLICATE_ASSET_CALENDAR")
        seen.add(aid)
        for key in ("work", "feed", "goods"):
            _need(isinstance(cal[key], dict), "MISSING_LEGACY_CALENDAR")
            for d, value in cal[key].items():
                _need(type(d) is int and 0 <= d <= 29, "INVALID_CALENDAR_DAY")
                if key == "goods":
                    _need(isinstance(value, dict), "INVALID_CALENDAR_GOODS")
                    for item, quantity in value.items():
                        _need(item in PRODUCTS, "UNKNOWN_CALENDAR_PRODUCT")
                        _qty(quantity, "calendar.goods")
                    goods.setdefault(d, Counter()).update(value)
                else:
                    _qty(value, "calendar." + key)
        work.update(cal["work"])
        feed.update(cal["feed"])
    return {"goods": _normal_sparse({d: dict(v) for d, v in goods.items()}),
            "work": _normal_sparse(dict(work)), "feed": _normal_sparse(dict(feed))}


def inventory_totals(observed_private):
    total = Counter()
    _need(isinstance(observed_private.get("shed"), dict), "MISSING_OBSERVED_SHED")
    _need(isinstance(observed_private.get("inventories"), list), "MISSING_OBSERVED_INVENTORIES")
    for source in [observed_private["shed"], *observed_private["inventories"]]:
        _need(isinstance(source, dict), "INVALID_OBSERVED_INVENTORY")
        for item, qty in source.items():
            _need(item in PRODUCTS | ANIMALS, "UNKNOWN_OBSERVED_INVENTORY_ITEM")
            total[item] += _qty(qty, "observed_inventory")
    return dict(total)


def validate_portfolio(portfolio, today, observed_private):
    """核原字段、来源集合及全期粮账。失败不改任何输入。"""
    cals = portfolio["calendars"]
    _need(isinstance(cals, list), "CALENDARS_NOT_LIST")
    coverage = portfolio["coverage_asset_ids"]
    _need(isinstance(coverage, list) and len(coverage) == len(set(coverage)), "INVALID_COVERAGE_IDS")
    _need(set(coverage) == {c["asset_id"] for c in cals}, "COVERAGE_ASSET_MISMATCH")
    aggregate = aggregate_calendars(cals)
    _need(set(portfolio["legacy_aggregate"]) == {"goods", "work", "feed"}, "LEGACY_AGGREGATE_KEYS")
    for key in ("goods", "work", "feed"):
        _need(aggregate[key] == _normal_sparse(portfolio["legacy_aggregate"][key]), "LEGACY_AGGREGATE_" + key.upper())
    _need(aggregate["work"] == _normal_sparse(portfolio["workload"]), "WORKLOAD_COVERAGE")
    labor = portfolio["labor"]
    capacity = _day_map(labor["capacity_by_day"], "capacity", today)
    cash = _day_map(labor["cash_by_day"], "hire_cash", today, numeric=True)
    _need(type(labor["feasible"]) is bool, "INVALID_LEGACY_FEASIBLE")
    old_feasible = all(portfolio["workload"].get(d, 0) <= capacity[d] for d in range(today, 30))
    _need(old_feasible == labor["feasible"], "LEGACY_FEASIBILITY_MISMATCH")
    _need(abs(labor["total_cost"] - sum(cash.values())) < 1e-9, "LEGACY_HIRE_TOTAL_MISMATCH")
    req = _day_map(portfolio["funding_requirements"], "requirements", today)
    funding = portfolio["funding_feed"]
    buys = _day_map(funding["buys_by_day"], "funding_buys", today)
    stocks = _day_map(funding["stock_by_day"], "funding_stock", today)
    costs = _day_map(funding["cash_by_day"], "funding_cash", today, numeric=True)
    _need(abs(funding["total_cash"] - sum(costs.values())) < 1e-9, "FUNDING_CASH_TOTAL_MISMATCH")
    held = inventory_totals(observed_private).get("WHEAT", 0)
    buffer = req[today] - aggregate["feed"].get(today, 0)
    _need(buffer >= 0, "NEGATIVE_BUFFER_DEBIT")
    for d in range(today, 30):
        if d > today:
            _need(req[d] == aggregate["feed"].get(d, 0), "FUTURE_REQUIREMENTS_NOT_COMPLETE_FEED:d%d" % d)
        _need(held + buys[d] - req[d] == stocks[d], "FUNDING_STOCK_IDENTITY:d%d" % d)
        _need((buys[d] == 0 and costs[d] == 0) or (buys[d] > 0 and costs[d] > 0), "FUNDING_BUY_CASH_IDENTITY:d%d" % d)
        held = stocks[d]
    _need(isinstance(portfolio["startup_fallback_days"], list) and
          all(type(d) is int and today <= d <= 29 for d in portfolio["startup_fallback_days"]), "INVALID_STARTUP_DAYS")
    pending = portfolio.get("pending_animal_units", {})
    _need(isinstance(pending, dict), "INVALID_PENDING_ANIMALS")
    for item, qty in pending.items():
        _need(item in ANIMALS, "INVALID_PENDING_ANIMAL_TYPE")
        _qty(qty, "pending_animal_units")
    _need(type(portfolio["conditional_prior_product_sales"]) is bool, "MISSING_PRIOR_SALES_CONDITION")
    return {"aggregate": aggregate, "buffer_debit": buffer,
            "legacy_sha256": canonical_sha({key: portfolio[key] for key in
                ("legacy_aggregate", "workload", "labor", "funding_requirements", "funding_feed")})}


def bind_day_materials(portfolio, today, day, observed_private, validated=None):
    """粮账不变；额外 buffer/carry 只占物理库存、不得获得第二份资金信用。"""
    _need(today < day <= 29, "MATERIAL_BINDING_FUTURE_ONLY")
    checked = validated or validate_portfolio(portfolio, today, observed_private)
    # 冻结首版 compiler 会在记录已知矛盾后继续推状态；不能借后日掩盖这个反例。
    # 未知 startup 只在外部逐日 fallback，不在这里等同于已知不可行历史。
    for cal in portfolio["calendars"]:
        for earlier, reasons in cal["unsupported_by_day"].items():
            if earlier < day and reasons:
                raise BindingError("KNOWN_IMPOSSIBLE_CALENDAR_HISTORY:%s:d%d:%s" %
                                   (cal["asset_id"], earlier, ",".join(reasons)))
    aggregate = checked["aggregate"]
    funding = portfolio["funding_feed"]
    buffer = checked["buffer_debit"]
    actual = inventory_totals(observed_private)
    prior = Counter()
    for d, goods in aggregate["goods"].items():
        if today <= d < day:
            prior.update(goods)
    sales = portfolio["conditional_prior_product_sales"]
    shed, reserve = {}, {}
    wheat_extra = 0 if sales else prior["WHEAT"]
    shed["WHEAT"] = funding["stock_by_day"][day - 1] + buffer + wheat_extra
    reserve["WHEAT"] = funding["stock_by_day"][day] + buffer + wheat_extra
    for item in ANIMALS:
        qty = actual.get(item, 0) + portfolio.get("pending_animal_units", {}).get(item, 0)
        if qty:
            shed[item] = reserve[item] = qty
    for item in PRODUCTS - {"WHEAT"}:
        quantity = actual.get(item, 0) + prior[item]
        if sales:
            quantity = min(12, quantity) if item == "FERTILIZER" else 0
        if quantity:
            shed[item] = reserve[item] = quantity
    conditions = [
        {"kind": "original_funding_feed_identity", "day": day,
         "paid_start_stock": funding["stock_by_day"][day - 1],
         "original_buy_qty": funding["buys_by_day"][day],
         "complete_feed_units": aggregate["feed"].get(day, 0),
         "paid_ending_stock": funding["stock_by_day"][day],
         "buffer_debit": buffer, "source_current_requirements": portfolio["funding_requirements"][today],
         "source_complete_current_feed": aggregate["feed"].get(today, 0),
         "additional_cash_credit": 0},
        {"kind": "conservative_physical_carry", "actual_private_sha256": canonical_sha(observed_private),
         "observed_total_inventory": actual, "prior_conditional_products": dict(prior),
         "pending_animal_units": deepcopy(portfolio.get("pending_animal_units", {})),
         "animal_carry_is_capacity_upper_bound_not_extra_productive_asset": True,
         "wheat_self_production_excluded_from_funding_sources": True},
        {"kind": "conditional_prior_delivery_and_sale" if sales else "prior_products_all_carried",
         "through_day": day - 1, "fertilizer_keep_cap": 12 if sales else None,
         "sales_cash_added_by_route_module": 0},
        {"kind": "caller_complete_portfolio", "asset_ids": sorted(portfolio["coverage_asset_ids"]),
         "actual_and_commitment_enumeration_is_external": True},
    ]
    buy = {"qty": funding["buys_by_day"][day], "estimated_cash": funding["cash_by_day"][day],
           "order_hour": 0, "available_from_hour": 1}
    return {"start_shed": {p: q for p, q in shed.items() if q},
            "reserved_shed": {p: q for p, q in reserve.items() if q},
            "planned_wheat_buy": buy, "conditional": conditions,
            "minimum_terminal_wheat": reserve["WHEAT"],
            "buffer_debit": buffer}


def _compact_stats_copy(stats):
    """只复制生产consumer所需的四项值，不向外共享可变商品字典。"""
    _need(isinstance(stats, dict), "COMPACT_STATS_INVALID")
    result = {"completed_service_count": _qty(stats["completed_service_count"], "COMPACT_SERVICE_COUNT")}
    for name in ("delivered_goods", "purchased_goods", "terminal_shed"):
        values = stats[name]
        _need(isinstance(values, dict), "COMPACT_STATS_INVALID:" + name)
        result[name] = {}
        for item, qty in values.items():
            _need(isinstance(item, str) and item in PRODUCTS | ANIMALS, "COMPACT_PRODUCT_INVALID")
            result[name][item] = _qty(qty, "COMPACT_PRODUCT_QUANTITY")
    return result


def _compact_entry(certificate, verification, problem_sha, implementation_ids):
    """仅在完整checker和原后验守卫全部通过后建立私有小记录。"""
    stats = verification["stats"]
    return {"schema": COMPACT_SCHEMA, "evidence_mode": COMPACT_MODE,
            "problem_sha256": problem_sha, "implementation_ids": dict(implementation_ids),
            "admission": IMPLEMENTATION_ID, "checker_valid": verification["valid"],
            "certificate_n_hands": certificate["n_hands"],
            "certificate_hire_cost": certificate["hire_cost"], "checker_hire_cost": stats["hire_cost"],
            "conditional_eod_overflow": dict(stats.get("conditional_eod_overflow", {})),
            "stats": _compact_stats_copy(stats)}


def _compact_public_stats(cached, problem_sha, implementation_ids, minimum_terminal_wheat):
    """命中仍核完整身份和已验证守卫；返回值与cache完全隔离。"""
    _need(isinstance(cached, dict) and cached.get("schema") == COMPACT_SCHEMA and
          cached.get("evidence_mode") == COMPACT_MODE, "COMPACT_CACHE_SCHEMA_MISMATCH")
    _need(cached.get("problem_sha256") == problem_sha and
          cached.get("implementation_ids") == implementation_ids and
          cached.get("admission") == IMPLEMENTATION_ID, "COMPACT_CACHE_IDENTITY_MISMATCH")
    _need(cached.get("checker_valid") is True and cached.get("certificate_n_hands") == 12 and
          cached.get("certificate_hire_cost") == 376 and cached.get("checker_hire_cost") == 376,
          "COMPACT_CACHE_GUARD_MISMATCH")
    overflow = cached.get("conditional_eod_overflow")
    _need(isinstance(overflow, dict) and all(type(q) is int and q == 0 for q in overflow.values()),
          "CONDITIONAL_EOD_OVERFLOW")
    _need(isinstance(cached.get("stats"), dict) and set(cached["stats"]) ==
          {"completed_service_count", "delivered_goods", "purchased_goods", "terminal_shed"},
          "COMPACT_STATS_INVALID")
    stats = _compact_stats_copy(cached["stats"])
    _need(stats["terminal_shed"].get("WHEAT", 0) >= minimum_terminal_wheat,
          "ENDING_WHEAT_RESERVED_SOURCE_SHORTFALL")
    return stats


class PlanRouteCache:
    """一次 economic_plan 独占；没有持久/跨帧缓存入口。"""
    def __init__(self, plan_token, current_day, observed_private, *, evidence_mode="full"):
        _need(isinstance(plan_token, str) and bool(plan_token), "EMPTY_PLAN_TOKEN")
        _need(type(evidence_mode) is str and evidence_mode in ("full", COMPACT_MODE), "INVALID_EVIDENCE_MODE")
        self.plan_token = plan_token
        self.evidence_mode = evidence_mode
        self.context_sha256 = canonical_sha({"token": plan_token, "day": current_day, "private": observed_private})
        self.entries = {}


def route_admission(baseline, trial, *, current_day, observed_private, plan_token,
                    cache=None, schedule=None, check=None, implementation_ids=None, evidence_mode="full"):
    """只返回劳动结论；原现金前缀仍须另过，失败不提交任何缓存或经营状态。"""
    result = {"schema": "r10-route-admission-result-v1", "status": "REJECTED",
              "labor_feasible_after_routes": False, "route_feasibility_by_day": {},
              "failed_day": None, "reason": None, "day_evidence": [],
              "scheduler_calls": 0, "checker_calls": 0, "cache_hits": 0,
              "cash_feasibility": "UNCHANGED_EXTERNAL_R9_PREFIX_REQUIRED",
              "candidate_calls": 0, "official_calls": 0}
    try:
        _need(type(current_day) is int and 0 <= current_day <= 29, "INVALID_CURRENT_DAY")
        _need(type(evidence_mode) is str and evidence_mode in ("full", COMPACT_MODE), "INVALID_EVIDENCE_MODE")
        compact = evidence_mode == COMPACT_MODE
        default_schedule = schedule is None
        default_check = check is None
        _need(not compact or (default_schedule and default_check), "COMPACT_MODE_REQUIRES_DEFAULT_IMPLEMENTATIONS")
        if schedule is None:
            from scheduler import schedule_day
            schedule = schedule_day
        if check is None:
            from checker import check_day
            check = check_day
        _need(isinstance(implementation_ids, dict) and implementation_ids.get("scheduler") and
              implementation_ids.get("checker") and implementation_ids.get("compiler"), "MISSING_IMPLEMENTATION_IDENTITIES")
        if compact:
            _need(all(type(k) is str and type(v) is str and v for k, v in implementation_ids.items()),
                  "COMPACT_IMPLEMENTATION_IDENTITIES_INVALID")
        context = canonical_sha({"token": plan_token, "day": current_day, "private": observed_private})
        if cache is not None:
            _need(isinstance(cache, PlanRouteCache) and cache.plan_token == plan_token and
                  cache.context_sha256 == context, "CACHE_CONTEXT_MISMATCH")
            _need(cache.evidence_mode == evidence_mode, "CACHE_EVIDENCE_MODE_MISMATCH")
        old = validate_portfolio(baseline, current_day, observed_private)
        new = validate_portfolio(trial, current_day, observed_private)
        old_by_id = {c["asset_id"]: c for c in baseline["calendars"]}
        new_by_id = {c["asset_id"]: c for c in trial["calendars"]}
        _need(set(old_by_id) <= set(new_by_id), "TRIAL_REMOVED_BASELINE_ASSET")
        for aid, cal in old_by_id.items():
            _need(cal == new_by_id[aid], "TRIAL_CHANGED_BASELINE_CALENDAR")
        result["baseline_legacy_sha256"] = old["legacy_sha256"]
        result["trial_legacy_sha256"] = new["legacy_sha256"]
        result["legacy_fields_unchanged"] = deepcopy({key: trial[key] for key in
            ("legacy_aggregate", "workload", "labor", "funding_requirements", "funding_feed")})
        failures = [d for d in range(current_day, 30)
                    if trial["workload"].get(d, 0) > trial["labor"]["capacity_by_day"][d]]
        if current_day in failures:
            result.update(failed_day=current_day, reason="CURRENT_DAY_FAILURE_UNCHANGED")
            return result
        if not failures:
            result.update(status="LEGACY_FEASIBLE_UNCHANGED", labor_feasible_after_routes=True)
            return result
        staged, evidence, admitted = {}, [], {}
        for day in failures:
            result["failed_day"] = day
            _need(trial["labor"]["cash_by_day"][day] == 376, "LEGACY_FAILED_DAY_NOT_12_HAND_COST_376")
            # 原模型的 10 个 h0 雇工 + 2 个 h1 雇工，不能伪造较小旧 capacity。
            slots = 23 if day == 29 else 24
            _need(trial["labor"]["capacity_by_day"][day] == slots + 10 * (slots - 1) + 2 * (slots - 2),
                  "LEGACY_FAILED_DAY_NOT_MAX_HAND_CAPACITY")
            materials = bind_day_materials(trial, current_day, day, observed_private, new)
            problem = compile_day_problem(trial["calendars"], day, current_day,
                materials["start_shed"], materials["reserved_shed"], materials["planned_wheat_buy"],
                trial["workload"].get(day, 0), trial["labor"]["cash_by_day"][day],
                conditional=materials["conditional"], startup_fallback_days=trial["startup_fallback_days"])
            _need(problem["status"] == "SUPPORTED", "UNSUPPORTED:" + ",".join(problem["unsupported_reasons"]))
            if compact:
                problem_sha = canonical_sha(problem)
                key = canonical_sha({"problem": problem, "implementations": implementation_ids,
                                     "admission": IMPLEMENTATION_ID, "n_hands": 12,
                                     "evidence_mode": COMPACT_MODE, "summary_schema": COMPACT_SCHEMA})
            else:
                key = canonical_sha({"problem": problem, "implementations": implementation_ids,
                                     "admission": IMPLEMENTATION_ID, "n_hands": 12})
            cached = cache.entries.get(key) if cache is not None else None
            if cached is None:
                result["scheduler_calls"] += 1
                certificate = schedule(problem if default_schedule else deepcopy(problem), 12)
                _need(certificate.get("status") == "FEASIBLE", "NO_CERTIFICATE:" + str(certificate.get("reason")))
                result["checker_calls"] += 1
                verification = check(problem if default_check else deepcopy(problem),
                                     certificate if default_check else deepcopy(certificate))
                _need(verification.get("valid") is True, "CHECKER_REJECTED:" + str(verification.get("errors")))
                _need(certificate["n_hands"] == 12 and certificate["hire_cost"] == 376 and
                      verification["stats"]["hire_cost"] == 376, "CERTIFICATE_CHANGED_HIRE_COST")
                _need(verification["stats"]["terminal_shed"].get("WHEAT", 0) >= materials["minimum_terminal_wheat"],
                      "ENDING_WHEAT_RESERVED_SOURCE_SHORTFALL")
                _need(not any(verification["stats"].get("conditional_eod_overflow", {}).values()), "CONDITIONAL_EOD_OVERFLOW")
                if compact:
                    cached = _compact_entry(certificate, verification, problem_sha, implementation_ids)
                    staged[key] = cached
                else:
                    cached = {"problem": problem, "certificate": certificate, "verification": verification}
                    staged[key] = deepcopy(cached)
            else:
                result["cache_hits"] += 1
            if compact:
                evidence.append({"day": day, "problem_sha256": problem_sha, "cache_key": key,
                                 "old_need": trial["workload"].get(day, 0),
                                 "old_capacity": trial["labor"]["capacity_by_day"][day],
                                 "old_hire_cash": 376, "buffer_debit": materials["buffer_debit"],
                                 "start_shed": dict(problem["start_shed"]), "reserved_shed": dict(problem["reserved_shed"]),
                                 "buy": dict(problem["planned_wheat_buy"]),
                                 "conditional_result": _compact_public_stats(cached, problem_sha, implementation_ids,
                                                                            materials["minimum_terminal_wheat"])})
            else:
                evidence.append({"day": day, "problem_sha256": canonical_sha(problem), "cache_key": key,
                                 "old_need": trial["workload"].get(day, 0),
                                 "old_capacity": trial["labor"]["capacity_by_day"][day],
                                 "old_hire_cash": 376, "buffer_debit": materials["buffer_debit"],
                                 "start_shed": problem["start_shed"], "reserved_shed": problem["reserved_shed"],
                                 "buy": problem["planned_wheat_buy"],
                                 "conditional_result": deepcopy(cached["verification"]["stats"])})
            admitted[day] = True
        if cache is not None:
            cache.entries.update(staged)
        result.update(status="CONDITIONAL_ROUTE_LABOR_FEASIBLE", labor_feasible_after_routes=True,
                      route_feasibility_by_day=admitted, day_evidence=evidence,
                      failed_day=None, reason=None)
        return result
    except (BindingError, KeyError, TypeError, ValueError, OverflowError) as exc:
        result["reason"] = str(exc)
        return result
