"""P2 有限控制。先核根 release；不重跑 P0/P1，不调用完整 agent 或引擎。"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import traceback

HERE = Path(__file__).resolve().parent
B = HERE.parents[1]
P1 = B / 'optimization_01/validation'
MODE = 'production_compact_v1'
SCHEMA = 'r10-production-evidence-summary-v1'
SMALL = ('completed_service_count', 'delivered_goods', 'purchased_goods', 'terminal_shed')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_helper(path, name):
    # 仅在 release 和全部附件 SHA 核对之后加载已冻结的审计工具。
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_gzip(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def create_suite(helper, decode):
    typed, differences = helper.typed, helper.differences

    class ObservedReturns(helper.NativeReferences):
        """沿用 P1 透明观察，另留逐日 checker 返回与 staged 内容快照。"""
        def __init__(self, ns, counts):
            super().__init__(ns, counts)
            self.rows = []
            self.route_code = ns['_r10_route_admission_route_admission'].__code__

        def callback(self, frame, event, arg):
            super().callback(frame, event, arg)
            name = self.codes.get(frame.f_code)
            if event == 'return' and name and isinstance(arg, dict):
                problem = frame.f_locals.get('problem', {})
                self.rows.append({'kind': name, 'day': arg.get('day', problem.get('day')),
                                  'status': arg.get('status'), 'valid': arg.get('valid'),
                                  'unsupported_reasons': deepcopy(arg.get('unsupported_reasons'))})
            if event == 'return' and frame.f_code is self.route_code:
                local = frame.f_locals
                self.route_return_locals = {
                    'staged': typed(local.get('staged', {})),
                    'admitted': typed(local.get('admitted', {})),
                    'evidence': typed(local.get('evidence', [])),
                }

    class P2Suite(helper.Suite):
        def __init__(self, freeze, out):
            super().__init__(freeze, out)
            self.namespaces = {}
            self.full_comparisons = {}
            self.compact_comparisons = {}

        def namespace(self, label):
            ns = super().namespace(label)
            self.namespaces[label] = ns
            self.check('candidate_id_is_registered', ns['CANDIDATE_ID'] == self.freeze['candidate_labels'][label])
            return ns

        def save(self):
            if self.active and self.active['id'] == 'P2_full_economic_once':
                self.active['purpose'] = 'P2 一次完整内部规划；离线对冻结 P1 全部输出，120 秒不放宽 1 秒'
            super().save()

        def compare_saved_full(self, fixture):
            for name in fixture['interface_case']['registered_cases']:
                self.active = {'id': 'P2_saved_P1_full_comparison_' + name, 'checks': {}}
                try:
                    self.verify()
                    path = self.freeze['references']['interfaces'][name]
                    old = read_gzip(path)
                    expected = (decode(old['result']), decode(old['cache']), old['result_reverse_alias_changes'])
                    present = ('P2', name) in self.live_results
                    self.check('new_full_case_completed', present)
                    ds = differences(expected, self.live_results[('P2', name)])
                    self.active.update(reference_path=path, reference_sha256=sha(path), differences=ds,
                                       side_labels={'P0': '已保存 P1', 'P1': '本次 P2'})
                    self.check('all_result_cache_and_alias_effect_exact', not ds, ds)
                    self.full_comparisons[name] = True
                except BaseException as exc:
                    self.full_comparisons[name] = False
                    self.failure(exc)
                finally:
                    self.save()

        def compact_projection(self, result, cache, full_name):
            full, full_cache, _ = self.live_results[('P2', full_name)]
            expected = deepcopy(full)
            expected_cache = {}
            for evidence in expected['day_evidence']:
                old_key = evidence['cache_key']
                row = full_cache[old_key]
                problem, cert, verification = row['problem'], row['certificate'], row['verification']
                new_key = canonical({'problem': problem, 'implementations': self.freeze['implementation_ids'],
                                     'admission': 'r10-route-admission-v1', 'n_hands': 12,
                                     'evidence_mode': MODE, 'summary_schema': SCHEMA})
                self.check('problem_hash_matches_frozen_full', evidence['problem_sha256'] == canonical(problem))
                stats = {k: deepcopy(verification['stats'][k]) for k in SMALL}
                expected_cache[new_key] = {
                    'schema': SCHEMA, 'evidence_mode': MODE, 'problem_sha256': canonical(problem),
                    'implementation_ids': deepcopy(self.freeze['implementation_ids']),
                    'admission': 'r10-route-admission-v1', 'checker_valid': verification['valid'],
                    'certificate_n_hands': cert['n_hands'], 'certificate_hire_cost': cert['hire_cost'],
                    'checker_hire_cost': verification['stats']['hire_cost'],
                    'conditional_eod_overflow': deepcopy(verification['stats'].get('conditional_eod_overflow', {})),
                    'stats': stats,
                }
                evidence['cache_key'] = new_key
                evidence['conditional_result'] = deepcopy(stats)
            ds = differences((expected, expected_cache), (result, cache))
            self.active['compact_full_projection_differences'] = ds
            self.check('only_registered_compact_fields_change', not ds, ds)

        def make_rollback_portfolio(self, ns, fixture):
            x = fixture['rollback_case']
            cals = []
            for pos in x['positions']:
                self.counts['pure_calendar_calls'] += 1
                cals.append(ns['_r10_calendar_compiler_project_calendar_with_services'](
                    deepcopy(x['tile']), x['today'], x['hour'], tuple(pos), deepcopy(x['calendar_condition'])))
            self.counts['pure_aggregate_calls'] += 1
            aggregate = ns['_r10_route_admission_aggregate_calendars'](cals)
            old = deepcopy(x['original_legacy_fields'])
            days = lambda mapping: {int(k): v for k, v in mapping.items()}
            for name in ('goods', 'work', 'feed'):
                old['legacy_aggregate'][name] = days(old['legacy_aggregate'][name])
            old['workload'] = days(old['workload'])
            for name in ('cash_by_day', 'capacity_by_day'):
                old['labor'][name] = days(old['labor'][name])
            old['funding_requirements'] = days(old['funding_requirements'])
            for name in ('buys_by_day', 'stock_by_day', 'cash_by_day'):
                old['funding_feed'][name] = days(old['funding_feed'][name])
            # JSON 旧证据只有值和顺序；不把保存值说成本次调用劳动函数的结果。
            self.check('regenerated_64_calendar_aggregate_matches_saved', aggregate == old['legacy_aggregate'])
            self.check('saved_work_matches_regenerated', aggregate['work'] == old['workload'])
            self.check('rollback_original_failed_day_numbers',
                       old['workload'][9] == 392 and old['workload'][10] == 784 and
                       old['labor']['capacity_by_day'][9] == old['labor']['capacity_by_day'][10] == 298)
            return {'calendars': cals, 'coverage_asset_ids': [c['asset_id'] for c in cals], **old,
                    'startup_fallback_days': deepcopy(x['startup_fallback_days']), 'pending_animal_units': {},
                    'conditional_prior_product_sales': True}

        def compact(self, fixture):
            ns = self.namespaces['P2']
            portfolio = decode(read_gzip(self.out / 'P2_pure_definition.json.gz')['portfolio'])
            common_cache = None
            cold_result = None
            for name in fixture['compact_cases']:
                self.active = {'id': 'P2_' + name, 'checks': {}, 'scope': '纯接口观察，不作延迟证据'}
                try:
                    self.verify()
                    rollback = name == 'compact_multiday_rollback'
                    x = fixture['rollback_case' if rollback else 'interface_case']
                    if rollback:
                        base = self.make_rollback_portfolio(ns, fixture)
                    else:
                        base = deepcopy(portfolio)
                    trial, private = deepcopy(base), deepcopy(x['private'])
                    if name in ('compact_cold', 'compact_multiday_rollback'):
                        self.counts['pure_cache_constructions'] += 1
                        cache = ns['_r10_route_admission_PlanRouteCache'](x['token'], x['today'], private, evidence_mode=MODE)
                    else:
                        if common_cache is None:
                            self.active['skipped'] = 'PENDING_COMPACT_COLD_FAILED'
                            self.compact_comparisons[name] = False
                            continue
                        cache = deepcopy(common_cache) if name == 'compact_cache_identity_mismatch' else common_cache
                    if name == 'compact_cache_identity_mismatch':
                        self.check('one_known_compact_entry', len(cache.entries) == 1)
                        next(iter(cache.entries.values()))['implementation_ids']['scheduler'] = 'deliberately_wrong_identity'
                    before = deepcopy((base, trial, private))
                    cache_before = deepcopy(cache.entries)
                    before_counts = self.counts.copy()
                    def forbidden_schedule(*args):
                        self.counts['compact_schedule_hook_calls'] += 1
                        raise AssertionError('COMPACT_HOOK_MUST_NOT_RUN')
                    def forbidden_check(*args):
                        self.counts['compact_check_hook_calls'] += 1
                        raise AssertionError('COMPACT_HOOK_MUST_NOT_RUN')
                    watch = ObservedReturns(ns, self.counts)
                    self.counts['pure_route_calls'] += 1
                    with watch:
                        result = ns['_r10_route_admission_route_admission'](
                            base, trial, current_day=x['today'], observed_private=private, plan_token=x['token'], cache=cache,
                            evidence_mode='full' if name == 'compact_cache_mode_mismatch' else MODE,
                            schedule=forbidden_schedule if name == 'compact_schedule_hook_rejected' else None,
                            check=forbidden_check if name == 'compact_check_hook_rejected' else None,
                            implementation_ids=self.freeze['implementation_ids'])
                    delta = dict(self.counts - before_counts)
                    self.active.update(result=typed(result), cache=typed(cache.entries),
                                       cache_before=typed(cache_before), count_delta=delta, observed_returns=watch.rows,
                                       route_return_locals=getattr(watch, 'route_return_locals', {}))
                    self.check('baseline_trial_private_unchanged', not differences(before, (base, trial, private)))
                    if name in ('compact_cold', 'compact_mutated_return_then_hit'):
                        self.check('compact_complete_success', result['labor_feasible_after_routes'] is True and
                                   result['route_feasibility_by_day'] == {29: True})
                        self.compact_projection(result, cache.entries,
                                                'default_cold' if name == 'compact_cold' else 'default_cache_hit')
                        if name == 'compact_cold':
                            cold_result = deepcopy(result)
                            snapshot = deepcopy(cache.entries)
                            for e in result['day_evidence']:
                                stats = e['conditional_result']
                                stats['completed_service_count'] = 999
                                for k in SMALL[1:]:
                                    stats[k]['MELON'] = 999
                                e['start_shed']['WHEAT'] = 888
                                e['reserved_shed']['WHEAT'] = 777
                                e['buy']['qty'] = 666
                            self.active['result_after_public_mutation'] = typed(result)
                            self.check('all_mutated_public_stats_and_witness_leave_cache_unchanged', not differences(snapshot, cache.entries))
                            self.check('public_mutation_leaves_input_unchanged', not differences(before, (base, trial, private)))
                            common_cache = cache
                        else:
                            self.check('cache_hit_no_solver', result['cache_hits'] == 1 and
                                       delta.get('pure_native_scheduler_calls', 0) == delta.get('pure_native_checker_calls', 0) == 0)
                            self.check('cache_hit_unchanged', not differences(cache_before, cache.entries))
                            self.check('hit_restores_all_witness_and_stats', not differences(cold_result['day_evidence'], result['day_evidence']))
                    elif rollback:
                        self.check('day9_scheduler_and_checker_actually_succeeded',
                                   any(r['kind'] == 'native_scheduler' and r['day'] == 9 and r['status'] == 'FEASIBLE' for r in watch.rows) and
                                   any(r['kind'] == 'native_checker' and r['day'] == 9 and r['valid'] is True for r in watch.rows))
                        self.check('day10_compiler_actually_rejected', any(r['kind'] == 'compile_day_problem' and
                                   r['day'] == 10 and r['status'] == 'UNSUPPORTED' and
                                   x['expected_rejection_reason_contains'] in r['unsupported_reasons'] for r in watch.rows))
                        local = watch.route_return_locals
                        staged, admitted = decode(local['staged']), decode(local['admitted'])
                        self.check('day9_success_reached_staged_before_failure', len(staged) == 1 and admitted == {9: True})
                        self.check('day10_failure_reason_exact', result['failed_day'] == 10 and
                                   x['expected_rejection_reason_contains'] in result['reason'])
                        self.check('staged_not_committed_on_later_failure', cache.entries == {} and
                                   result['route_feasibility_by_day'] == {} and result['day_evidence'] == [] and
                                   result['labor_feasible_after_routes'] is False)
                        self.check('rollback_only_one_solver_pair', delta.get('pure_native_scheduler_calls') ==
                                   delta.get('pure_native_checker_calls') == 1 and delta.get('pure_compile_day_problem_calls') == 2)
                    else:
                        reason = {'compact_cache_mode_mismatch': 'CACHE_EVIDENCE_MODE_MISMATCH',
                                  'compact_cache_identity_mismatch': 'COMPACT_CACHE_IDENTITY_MISMATCH',
                                  'compact_schedule_hook_rejected': 'COMPACT_MODE_REQUIRES_DEFAULT_IMPLEMENTATIONS',
                                  'compact_check_hook_rejected': 'COMPACT_MODE_REQUIRES_DEFAULT_IMPLEMENTATIONS'}[name]
                        self.check('explicit_rejection_reason', result['reason'] == reason and not result['labor_feasible_after_routes'])
                        self.check('rejection_no_solver_or_checker', delta.get('pure_native_scheduler_calls', 0) ==
                                   delta.get('pure_native_checker_calls', 0) == 0)
                        self.check('rejection_cache_unchanged', not differences(cache_before, cache.entries))
                        self.check('rejection_hooks_not_called', self.counts['compact_schedule_hook_calls'] ==
                                   self.counts['compact_check_hook_calls'] == 0)
                    self.compact_comparisons[name] = True
                except BaseException as exc:
                    self.compact_comparisons[name] = False
                    self.failure(exc)
                finally:
                    self.save()

    return P2Suite


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--freeze', type=Path, required=True)
    args = ap.parse_args()
    raw = args.freeze.read_bytes()
    frozen = json.loads(raw)
    if frozen.get('schema') != 'r10-p2-validation-freeze-v1' or frozen.get('root_execution_release') is not True:
        raise SystemExit('ROOT_RELEASE_REQUIRED')
    for path, expected in frozen['files'].items():
        if sha(path) != expected:
            raise SystemExit('SOURCE_SHA_MISMATCH:' + path)
    assert frozen['files'][str(Path(__file__).resolve())] == sha(__file__)
    helper = load_helper(frozen['helper_path'], '_p2_frozen_p1_audit_helper')
    reader = load_helper(frozen['decoder_path'], '_p2_frozen_typed_decoder')
    decode = reader.decode
    out = Path(frozen['output_path'])
    out.mkdir(parents=True, exist_ok=False)
    fixture = json.loads(Path(frozen['fixture_path']).read_bytes())
    suite = create_suite(helper, decode)(frozen, out)
    top_error = None
    try:
        suite.pure('P2', fixture)
        suite.compare_saved_full(fixture)
        suite.compact(fixture)
        print(json.dumps({'stage': 'pure_complete', 'counts': dict(suite.counts), 'errors': len(suite.errors)}, ensure_ascii=False), flush=True)
        suite.full_economic('P2', fixture)
    except BaseException as exc:
        top_error = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        if suite.active:
            suite.failure(exc)
            suite.save()
    prior = read_gzip(frozen['references']['full_economic'])
    reference = (decode(prior['plan']), decode(prior['state']))
    returned = 'P2' in suite.economic
    ds = helper.differences(reference, suite.economic['P2'], 'entire_plan_and_state') if returned else None
    audit = suite.economic['P2'][1]['investment_receipts'][-1]['r10_future_route'] if returned else {}
    expected_counts = frozen['expected_economic_counts']
    actual_counts = {k: audit.get(k) for k in expected_counts}
    full_counts_equal = returned and actual_counts == expected_counts
    drift = [p for p, value in frozen['files'].items() if sha(p) != value]
    if args.freeze.read_bytes() != raw:
        drift.append(str(args.freeze))
    count_overruns = {key: {'actual': suite.counts[key], 'maximum': maximum}
                      for key, maximum in frozen['maximum_calls'].items() if suite.counts[key] > maximum}
    complete_matrix = (len(suite.full_comparisons) == 4 and all(suite.full_comparisons.values()) and
                       len(suite.compact_comparisons) == 7 and all(suite.compact_comparisons.values()))
    eq = bool(complete_matrix and returned and not ds and full_counts_equal and not
              (suite.errors or top_error or drift or count_overruns))
    performance_pass = bool(suite.performance.get('P2', {}).get('returned') and not suite.performance['P2']['over_1s'])
    status = 'EQUIVALENCE_OR_SOURCE_FAILURE' if not eq else 'P2_TIME_THRESHOLD_FAILED' if not performance_pass else 'P2_BOUNDED_CONTROL_PASSED_NOT_QUALIFICATION'
    result = {'schema': 'r10-p2-validation-result-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'freeze_sha256': hashlib.sha256(raw).hexdigest(), 'status': status, 'counts': dict(suite.counts),
              'count_overruns': count_overruns, 'records': suite.results, 'errors': suite.errors, 'top_error': top_error,
              'source_drift': drift, 'full_interface_saved_P1_comparison': suite.full_comparisons,
              'compact_interface_checks': suite.compact_comparisons,
              'full_economic_equivalence': {'P2_returned': returned, 'exact_entire_typed_plan_state_equal': returned and not ds,
                                           'differences': ds, 'side_labels': {'P0': '已保存 P1', 'P1': '本次 P2'},
                                           'expected_counts': expected_counts, 'actual_counts': actual_counts,
                                           'complete_economic_counts_equal': full_counts_equal,
                                           'saved_P1_reference_path': frozen['references']['full_economic'],
                                           'saved_P1_plan_sha256': prior['plan_sha256'], 'saved_P1_state_sha256': prior['state_sha256']},
              'unprofiled_internal_performance': suite.performance,
              'saved_P1_performance_reference': {k: prior[k] for k in ('seconds', 'over_1s', 'returned')},
              'P2_internal_within_1s': performance_pass, 'equivalence_and_source_integrity_pass': eq,
              'P0_calls': 0, 'P1_calls': 0, 'whole_agent_calls': 0, 'official_calls': 0, 'new_complete_matches': 0,
              'scope': '纯接口计数与完整规划内后代计数分开；只作一次优化等价/时延控制，不是正式门控或金牌结论。'}
    (out / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'summary': str(out / 'summary.json'), 'status': status, 'counts': dict(suite.counts),
                      'P2_returned': returned, 'full_exact_equal': returned and not ds,
                      'errors': len(suite.errors), 'source_drift': drift}, ensure_ascii=False), flush=True)
    return int(not eq or not performance_pass)


if __name__ == '__main__':
    raise SystemExit(main())
