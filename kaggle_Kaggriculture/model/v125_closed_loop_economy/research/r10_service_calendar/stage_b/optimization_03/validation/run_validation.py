"""P3 唯一有限控制；根 release 前拒绝加载候选。"""
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import traceback

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_record(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def make_suite(helper, normalize):
    typed, differences = helper.typed, helper.differences

    class P3Suite(helper.Suite):
        def __init__(self, frozen, out):
            super().__init__(frozen, out)
            self.comparisons = {}
            self.pure_pass = False

        def namespace(self, label):
            ns = super().namespace(label)
            self.check('registered_candidate_id', ns['CANDIDATE_ID'] == self.freeze['candidate_id'])
            self.check('last_callable_is_agent', [x for x in ns.values() if callable(x)][-1] is ns['agent'])
            return ns

        def save(self):
            if self.active and self.active['id'].endswith('_full_economic_once'):
                self.active['purpose'] = 'P3 固定人工输入一次完整经济调用；不加profile，1秒要求不变'
            super().save()

        def selector(self, fixture):
            self.active = {'id': 'P3_pure_selector', 'checks': {}, 'scope': '合成报价/真实生产helper，0solver'}
            try:
                ns = self.namespace('selector')
                st, obs0, offers = {}, deepcopy(fixture['pure_observation']), {}
                rows = []
                for seat, names in ((0, ('A', 'B', 'C')), (1, ('A', 'B'))):
                    obs = deepcopy(obs0)
                    obs['player'] = seat
                    for name in names:
                        q = deepcopy(next(row for row in fixture['pure_offers'] if row['name'] == name))
                        q['position'] = tuple(q['position'])
                        self.counts['pure_key_calls'] += 1
                        q['_r10_rescue_key'] = ns['_r10_integration_rescue_key'](obs, q['item'], q['position'])
                        offers[(seat, name)] = q
                changed = deepcopy(obs0)
                changed.update(step=216, day=9, hour=0)
                changed['farms'][0]['farmer'] = [7, 7]
                changed['market']['prices']['MELON'] = 200
                self.counts['pure_key_calls'] += 1
                stable = ns['_r10_integration_rescue_key'](changed, 'MELON', (0, 0))
                self.check('key_stable_under_clock_price_and_movement', stable == offers[(0, 'A')]['_r10_rescue_key'])
                changed['farms'][0]['tiles'][0][0] = {'kind': 'WEED'}
                self.counts['pure_key_calls'] += 1
                different = ns['_r10_integration_rescue_key'](changed, 'MELON', (0, 0))
                self.check('key_changes_with_target_kind', different != stable)
                self.check('key_is_seat_scoped', offers[(0, 'A')]['_r10_rescue_key'] != offers[(1, 'A')]['_r10_rescue_key'])
                self.active['key_results'] = {'base_keys': {str(k): q['_r10_rescue_key'] for k, q in offers.items()},
                                              'after_clock_price_movement': stable, 'after_kind_change': different}
                self.active['sequence'] = rows
                for index, control in enumerate(fixture['pure_sequence'], 1):
                    obs = deepcopy(obs0)
                    obs.update(step=control['step'], day=control['step'] // 24, hour=control['step'] % 24,
                               player=control['seat'])
                    if control['step'] >= 216:
                        obs['farms'][0]['farmer'] = [7, 7]
                        obs['market']['prices']['MELON'] = 200
                    selected_offers = [offers[(control['seat'], name)] for name in control['offers']]
                    before_offers, before_state = deepcopy(selected_offers), deepcopy(st)
                    self.counts['pure_select_calls'] += 1
                    result = ns['_r10_integration_select_rescue'](st, obs, selected_offers)
                    cycle = result['cycle']
                    row = {'index': index, 'input': control, 'before_state': typed(before_state),
                           'result_before_failure': typed(result), 'state_after_select': typed(st)}
                    rows.append(row)
                    self.check(str(index) + '_offers_unmodified', not differences(before_offers, selected_offers))
                    self.check(str(index) + '_cycle_is_seat_state', cycle is st['_r10_rescue_cycles'][str(control['seat'])])
                    if 'expect' in control:
                        target = offers[(control['seat'], control['expect'])]
                        self.check(str(index) + '_expected_original_q_reference', result['q'] is target)
                        self.check(str(index) + '_proposal_is_uncertified', result['status'] == 'SELECTED_UNCERTIFIED_RESCUE')
                    else:
                        self.check(str(index) + '_same_frame_refused', result['q'] is None and result['status'] == control['expect_status'])
                    if 'expected_cycle' in control:
                        self.check(str(index) + '_cycle_index', cycle['index'] == control['expected_cycle'])
                    if index == 4:
                        self.check('new_C_precedes_reset_A', cycle['index'] == 0 and cycle['reset_after_step'] is None)
                    if index == 7:
                        self.check('seat1_does_not_mutate_seat0', not differences(before_state['_r10_rescue_cycles']['0'], st['_r10_rescue_cycles']['0']))
                    if control.get('fail'):
                        self.counts['pure_fail_calls'] += 1
                        ns['_r10_integration_fail_rescue'](cycle, obs, result['q']['_r10_rescue_key'],
                                                          [q['_r10_rescue_key'] for q in selected_offers])
                        self.check(str(index) + '_failed_key_saved', result['q']['_r10_rescue_key'] in cycle['failed_keys'])
                    row['state_after_failure_registration'] = typed(st)
                self.active['final_state'] = typed(st)
                self.check('exact_pure_call_counts', self.counts['pure_select_calls'] == 8 and
                           self.counts['pure_fail_calls'] == 3 and self.counts['pure_key_calls'] == 7)
                self.pure_pass = True
            except BaseException as exc:
                self.failure(exc)
            finally:
                self.save()

        def original_business(self, plan, state, fixture):
            p, s = deepcopy(normalize(plan)), deepcopy(normalize(state))
            removed = {'plan': {}, 'state': {}, 'receipts': []}
            for key in fixture['new_plan_fields']:
                self.check('new_plan_field_' + key + '_present', key in p)
                removed['plan'][key] = p.pop(key)
                self.check('latest_plan_new_field_' + key + '_present', key in s['latest_investment_plan'])
                s['latest_investment_plan'].pop(key)
            for key in fixture['new_state_fields']:
                self.check('new_state_field_' + key + '_present', key in s)
                removed['state'][key] = s.pop(key)
            for receipt in s['investment_receipts']:
                extra = {}
                for key in fixture['new_receipt_fields']:
                    self.check('new_receipt_field_' + key + '_present', key in receipt)
                    extra[key] = receipt.pop(key)
                removed['receipts'].append(extra)
            return p, s, removed

        def review_economic(self, case, fixture):
            label = case['id']
            self.active = {'id': label + '_offline_comparison', 'checks': {}}
            try:
                self.verify()
                self.check('complete_output_available', label in self.economic)
                plan, state = self.economic[label]
                receipt = state['investment_receipts'][-1]
                self.check('audit_structures_present', isinstance(receipt.get('r10_future_route'), dict) and
                           isinstance(receipt.get('r10_rescue'), dict) and
                           isinstance(receipt['r10_future_route'].get('counts'), dict))
                audit, rescue = receipt['r10_future_route'], receipt['r10_rescue']
                counts = audit['counts']
                self.check('audit_counts_nonnegative_int', all(type(v) is int and v >= 0 for v in counts.values()))
                self.check('rescue_flags_boolean', type(rescue.get('route_attempted')) is bool and type(rescue.get('approved')) is bool)
                if rescue['route_attempted']:
                    self.check('attempt_has_explicit_actual_count', counts.get('route_attempts') == 1)
                    self.check('native_counts_explicit_after_attempt', all(k in counts for k in ('scheduler_calls', 'checker_calls')))
                    self.check('one_route_outcome_recorded', counts.get('route_successful_quotes', 0) + counts.get('route_failed_quotes', 0) == 1)
                    actual = {k: counts[k] for k in ('route_attempts', 'scheduler_calls', 'checker_calls')}
                else:
                    self.check('no_attempt_proves_zero', not rescue['approved'] and all(value == 0 for value in counts.values()))
                    actual = {'route_attempts': 0, 'scheduler_calls': 0, 'checker_calls': 0}
                self.active['actual_counts'] = actual
                self.check('per_frame_route_bound', actual['route_attempts'] <= 1)
                self.check('per_route_day_bound', actual['scheduler_calls'] <= case['max_daily_solvers'] and
                           actual['checker_calls'] <= case['max_daily_solvers'])
                self.check('expected_cheap_batch_count', rescue['cheap_accepted_count'] == case['expected_cheap_admissions'])
                self.check('exact_zero_or_one_additional_permit', len(plan['admitted_investments']) ==
                           rescue['cheap_accepted_count'] + int(rescue['approved']))
                self.active.update(actual_counts=actual, original_audit_counts=counts, rescue=normalize(rescue),
                                   original_receipt=normalize(receipt), current_observation_unchanged=self.performance[label]['observation_unchanged'])
                self.check('observation_unmodified', self.performance[label]['observation_unchanged'])
                old = read_record(case['reference_path'])
                if case['reference_kind'] == 'full_legacy_plan_state':
                    baseline = next(row for row in old['modes'] if row['mode'] == 'legacy')
                    p, s, removed = self.original_business(plan, state, fixture)
                    ds = differences((baseline['plan'], baseline['state_after']), (p, s))
                    self.active.update(original_business_differences=ds, explicitly_added_fields=removed,
                                       comparison_representation='冻结旧normalizer同JSON表达；不是旧输出未保存的完整Python类型证明')
                    if not rescue['approved']:
                        self.check('no_rescue_all_original_business_fields_equal', not ds, ds)
                    else:
                        self.active['business_equality_status'] = 'CHANGED_BY_ONE_APPROVED_RESCUE_NOT_EQUIVALENCE_TARGET'
                else:
                    baseline = old['R9_diagnostics']['0']['investment_receipts'][0]
                    before = deepcopy(baseline)
                    for key in fixture['receipt_downstream_only_fields']:
                        before.pop(key, None)
                    after = deepcopy(normalize(receipt))
                    for key in fixture['new_receipt_fields']:
                        after.pop(key)
                    ds = differences(before, after)
                    self.active.update(original_economic_receipt_differences=ds, original_complete_state='NOT_SAVED_NOT_COMPARED')
                    self.check('all_original_24_permits_exact_in_order', normalize(receipt['admitted'][:24]) == baseline['admitted'])
                    stable_keys = ('step', 'expert', 'selection_objective', 'selected_expert_score', 'expert_selection_scores',
                                   'actual_cash', 'actual_wheat', 'existing', 'initial_funding_book', 'credit_source_positions')
                    self.check('all_stable_cheap_receipt_fields_equal', all(normalize(receipt[k]) == baseline[k] for k in stable_keys))
                    if not rescue['approved']:
                        self.check('no_rescue_original_economic_receipt_equal', not ds, ds)
                if rescue['approved']:
                    proof = audit.get('last_accepted_proof')
                    self.check('approved_has_successful_complete_proof', isinstance(proof, dict) and
                               proof.get('labor_feasible_after_routes') is True and not audit['unrepresented_commitments'])
                    day = case['observation']['day']
                    self.check('approved_never_changes_current_day_failure', all(d > day for d in audit['final_legacy_failed_days']))
                    self.check('all_final_failed_days_have_proof', all(proof['route_feasibility_by_day'].get(d) is True
                               for d in audit['final_legacy_failed_days']) and audit['final_effective_labor_feasible'] is True)
                    own = case['observation']['farms'][case['observation']['player']]
                    assets = sum(isinstance(tile, dict) and (tile.get('kind') == 'PLANT' or 'animal' in tile)
                                 for row in own['tiles'] for tile in row)
                    self.check('approved_observed_asset_count_complete', counts.get('actual_calendar_compilations') == assets)
                    expected_sources = receipt['existing']['transit_project_count'] + receipt['existing']['contract_count'] + len(receipt['admitted'])
                    self.check('approved_committed_sources_count_complete', audit['source_quote_count'] == expected_sources)
                    q = plan['admitted_investments'][-1]
                    self.check('approved_funding_receipt_matches_q', q['funding_admission'] is not None and
                               receipt['funding_admissions'][-1]['status'] == q['funding_admission'])
                    self.active['post_route_cash_branch'] = 'APPROVED_SAME_Q_PREFIX_BRANCH_BY_FROZEN_SOURCE_AND_SAVED_OUTPUT'
                    self.active['full_intermediate_trial_snapshot'] = 'PENDING_NOT_CAPTURED_WITHOUT_PROFILE'
                else:
                    self.active['post_route_cash_branch'] = 'REJECTION_BRANCH_RECORDED' if rescue['status'] == 'POST_ROUTE_CASH_REJECTED' else 'PENDING_BRANCH_NOT_COVERED'
                self.comparisons[label] = {'passed': True, 'counts': actual, 'rescue_approved': rescue['approved'],
                                           'rescue_status': rescue['status'], 'cheap_accepted_count': rescue['cheap_accepted_count'],
                                           'post_route_cash_branch': self.active['post_route_cash_branch']}
            except BaseException as exc:
                self.failure(exc)
                self.comparisons[label] = {'passed': False, 'counts': self.active.get('actual_counts'), 'error': str(exc)}
            finally:
                self.save()

    return P3Suite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', type=Path, required=True)
    args = parser.parse_args()
    raw = args.freeze.read_bytes()
    frozen = json.loads(raw)
    if frozen.get('schema') != 'r10-p3-validation-freeze-v1' or frozen.get('root_execution_release') is not True:
        raise SystemExit('ROOT_RELEASE_REQUIRED')
    for path, expected in frozen['files'].items():
        if sha(path) != expected:
            raise SystemExit('SOURCE_SHA_MISMATCH:' + path)
    assert frozen['files'].get(str(Path(__file__).resolve())) == sha(__file__)
    helper = load(frozen['helper_path'], '_p3_frozen_p1_tools')
    normalizer = load(frozen['normalizer_path'], '_p3_frozen_old_json_normalizer')
    fixture = json.loads(Path(frozen['fixture_path']).read_bytes())
    out = Path(frozen['output_path'])
    out.mkdir(parents=True, exist_ok=False)
    suite = make_suite(helper, normalizer.normalize)(frozen, out)
    top_error = None
    try:
        suite.selector(fixture)
        for case in fixture['cases']:
            label = case['id']
            suite.full_economic(label, {'economic_case': {'observation': case['observation']},
                                        'economic_timeout_seconds': fixture['economic_timeout_seconds']})
            suite.review_economic(case, fixture)
            print(json.dumps({'case': label, 'performance': suite.performance.get(label),
                              'comparison': suite.comparisons.get(label)}, ensure_ascii=False), flush=True)
    except BaseException as exc:
        top_error = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        if suite.active:
            suite.failure(exc)
            suite.save()
    drift = [path for path, expected in frozen['files'].items() if sha(path) != expected]
    if args.freeze.read_bytes() != raw:
        drift.append(str(args.freeze))
    overruns = {k: {'actual': suite.counts[k], 'max': maximum} for k, maximum in frozen['maximum_direct_calls'].items()
                if suite.counts[k] > maximum}
    counted = [v['counts'] for v in suite.comparisons.values() if isinstance(v.get('counts'), dict)]
    known_totals = {k: sum(v[k] for v in counted) for k in ('route_attempts', 'scheduler_calls', 'checker_calls')}
    totals_complete = len(counted) == 5
    totals = known_totals if totals_complete else None
    complete = len(suite.comparisons) == 5 and all(v['passed'] for v in suite.comparisons.values())
    bounds = totals_complete and totals['route_attempts'] <= 5 and totals['scheduler_calls'] <= 110 and totals['checker_calls'] <= 110
    evidence_pass = bool(suite.pure_pass and complete and bounds and not (suite.errors or top_error or drift or overruns))
    perf_pass = len(suite.performance) == 5 and all(v['returned'] and not v['over_1s'] for v in suite.performance.values())
    status = 'ENGINEERING_EVIDENCE_FAILURE' if not evidence_pass else 'P3_TIME_THRESHOLD_FAILED' if not perf_pass else 'P3_BOUNDED_INTERNAL_CONTROLS_PASSED_NOT_FULL_AGENT_OR_QUALIFICATION'
    result = {'schema': 'r10-p3-validation-result-v1', 'at': datetime.now(timezone.utc).isoformat(),
              'freeze_sha256': hashlib.sha256(raw).hexdigest(), 'status': status,
              'counts': dict(suite.counts), 'economic_nested_count_totals': totals,
              'nested_counts_complete': totals_complete, 'known_case_nested_counts': known_totals,
              'direct_count_overruns': overruns, 'records': suite.results, 'errors': suite.errors,
              'top_error': top_error, 'source_drift': drift, 'pure_selector_pass': suite.pure_pass,
              'case_comparisons': suite.comparisons, 'unprofiled_performance': suite.performance,
              'evidence_and_source_integrity_pass': evidence_pass, 'all_five_internal_calls_within_1s': perf_pass,
              'full_agent_calls': 0, 'engine_calls': 0, 'new_complete_matches': 0,
              'P0_P1_P2_R9_calls': 0, 'scope': '五个人工输入的有限内部工程控制；缺失中间trial证据明示pending，非比赛或金牌结论。'}
    (out / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'summary': str(out / 'summary.json'), 'status': status, 'counts': dict(suite.counts),
                      'nested_counts': totals}, ensure_ascii=False), flush=True)
    return int(not evidence_pass or not perf_pass)


if __name__ == '__main__':
    raise SystemExit(main())
