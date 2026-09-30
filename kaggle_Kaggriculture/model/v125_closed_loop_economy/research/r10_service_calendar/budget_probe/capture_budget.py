#!/usr/bin/env python3
"""对已存动作作一次只读内部报价捕获；不生成独立比赛。"""
from __future__ import annotations
import argparse, collections, copy, gzip, hashlib, importlib.util, json, os, sys, traceback, types
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
REASONS = {'labor', 'cash_prefix', 'startup_or_maturity', 'nonpositive_net'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def plain(value):
    return json.loads(json.dumps(value, allow_nan=False))

def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def failures(work, capacities, day):
    """只比较原函数的输入/返回；不重算候选调度。"""
    if set(capacities) != set(range(day, 30)):
        raise RuntimeError('INCOMPLETE_CAPACITY_DAYS')
    return [{'day': d, 'need': max(0, work.get(d, 0)), 'capacity': capacities[d],
             'deficit': max(0, work.get(d, 0)) - capacities[d]}
            for d in range(day, 30) if max(0, work.get(d, 0)) > capacities[d]]

def failure_class(rows, day):
    current = any(r['day'] == day for r in rows)
    future = any(r['day'] > day for r in rows)
    return ('current_and_future' if future else 'current_only') if current else ('future_only' if future else 'none')

def contract_summary(st):
    contracts = st.get('contracts', {})
    return {'count': len(contracts), 'by_kind': dict(collections.Counter(c.get('kind', 'UNKNOWN') for c in contracts.values())),
            'items': [{'unit': u, **{k: plain(c[k]) for k in ('target', 'kind', 'accepted_step', 'expires', 'phase', 'route_phase') if k in c}}
                      for u, c in contracts.items()]}

class BudgetProfiler:
    def __init__(self, code, callsites):
        self.code, self.callsites = code, callsites
        self.step = -1
        self.rows = []
        self.counts = collections.Counter()
        self.total = 0
        self.samples = {}

    def begin(self, step):
        self.step, self.rows, self.counts, self.total = step, [], collections.Counter(), 0

    def profile(self, frame, event, result):
        if event != 'return' or frame.f_code is not self.code:
            return
        loc = frame.f_locals
        q, reason = result
        if reason is not None and reason not in REASONS:
            raise RuntimeError('UNKNOWN_QUOTE_REASON')
        obs = loc['obs']
        if obs['step'] != self.step:
            raise RuntimeError('PROFILE_STEP_CHANGED')
        line = frame.f_back.f_lineno
        if line not in self.callsites:
            raise RuntimeError(f'UNKNOWN_QUOTE_CALLSITE {line}')
        self.total += 1
        self.counts[reason or 'accepted_quote'] += 1
        base = {'step': self.step, 'day': obs['day'], 'hour': obs['hour'], 'item': loc['item'],
                'position': list(loc['pos']), 'callsite_line': line, 'phase': self.callsites[line],
                'quote_ordinal_in_step': self.total, 'reason': reason,
                'actual_cash': obs['farms'][obs['player']]['money']}
        if q is not None:
            base['quote'] = {k: q[k] for k in ('build_first', 'start_step_model', 'first_product_day', 'fixed_cash',
                              'gross_cash_model', 'net_cash_model', 'cash_reserved_model', 'hire_cash_model', 'labor',
                              'selection_score') if k in q}
        if reason == 'labor':
            labor, base_labor, next_work, work = loc['labor'], loc['base_labor'], loc['next_work'], loc['workload']
            rows = failures(next_work, labor['capacity_by_day'], obs['day'])
            baseline = failures(work, base_labor['capacity_by_day'], obs['day'])
            if not rows or labor['feasible'] or bool(baseline) == bool(base_labor['feasible']):
                raise RuntimeError('LABOR_FEASIBILITY_INCONSISTENT')
            for row in rows:
                d = row['day']
                row.update(base_need=work.get(d, 0), base_capacity=base_labor['capacity_by_day'][d],
                           added_work=next_work.get(d, 0) - work.get(d, 0),
                           quote_calendar_work=q['calendar']['work'].get(d, 0))
            base.update(failure_class=failure_class(rows, obs['day']), first_failure_day=rows[0]['day'],
                        first_failure_offset=rows[0]['day'] - obs['day'], failure_days=rows,
                        baseline_failure_days=baseline, baseline_already_infeasible=bool(baseline),
                        current_day={'base_need': work.get(obs['day'], 0), 'trial_need': next_work.get(obs['day'], 0),
                                     'base_capacity': base_labor['capacity_by_day'][obs['day']],
                                     'trial_capacity': labor['capacity_by_day'][obs['day']]},
                        existing_hands=len(obs['farms'][obs['player']]['hands']),
                        base_order_slots=len(loc['material_order_keys']), trial_order_slots=len(loc['next_keys']),
                        current_hire_target=labor['hire_target_today'],
                        funding_evaluation='NOT_EVALUATED_ORIGINAL_SHORT_CIRCUIT',
                        economic_net_checked=False)
            self.rows.append(base)
        sample_key = (reason or 'accepted_quote', self.callsites[line])
        if sample_key not in self.samples:
            self.samples[sample_key] = plain(base)

def aggregate(rows):
    counts = collections.Counter()
    offsets = collections.Counter()
    items = collections.defaultdict(collections.Counter)
    hours = collections.defaultdict(collections.Counter)
    days = collections.defaultdict(collections.Counter)
    examples = {}
    for r in rows:
        group = r['failure_class']
        counts[group] += 1
        counts['baseline_already_infeasible' if r['baseline_already_infeasible'] else 'baseline_feasible'] += 1
        offsets[r['first_failure_offset']] += 1
        items[r['item']][group] += 1
        hours[r['hour']][group] += 1
        days[r['day']][group] += 1
        if r['quote']['net_cash_model'] > 0:
            counts['positive_modeled_net_before_cash_check'] += 1
        label = (group, r['baseline_already_infeasible'])
        examples.setdefault(str(label), r)
    return {'labor_rejections': len(rows), 'counts': dict(counts), 'first_failure_day_offset': dict(offsets),
            'by_item': {k: dict(v) for k, v in items.items()}, 'by_hour': {k: dict(v) for k, v in hours.items()},
            'by_decision_day': {k: dict(v) for k, v in days.items()}, 'examples': list(examples.values()),
            'counting_unit': '原函数报价尝试；跨帧、站点和报价/复查可能重复，不能解释为独立项目或收益机会数',
            'scope': '原R9模型内部约束定位；不证明真实劳动可行性，也不证明已拒报价的现金可行性'}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--freeze', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    sys.dont_write_bytecode = True
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError('REFUSE_EXISTING_OUTPUT')
    out.mkdir(parents=True, exist_ok=True)
    freeze_bytes = args.freeze.read_bytes()
    freeze = json.loads(freeze_bytes)
    guards = {**freeze['files'], str(args.freeze.resolve()): hashlib.sha256(freeze_bytes).hexdigest()}
    calls = steps = compared = receipts_checked = snapshots_checked = 0
    all_rows, step_rows = [], []
    reason_totals = collections.Counter()
    agent = profiler = engine = h = None
    failure = None
    try:
        for path, expected in guards.items():
            if sha(path) != expected:
                raise RuntimeError(f'FROZEN_FILE_CHANGED {path}')
        if guards[str(Path(__file__).resolve())] != sha(__file__):
            raise RuntimeError('SCRIPT_NOT_FROZEN')
        run = Path(freeze['source_run'])
        manifest = json.loads((run / 'run_manifest.json').read_bytes())
        games = [json.loads(line) for line in (run / 'games.jsonl').read_text().splitlines() if line.strip()]
        if len(games) != 1:
            raise RuntimeError('EXPECTED_EXACTLY_ONE_SOURCE_GAME')
        game = games[0]
        tracepath = Path(game['trace']['path'])
        trace = json.loads(gzip.decompress(tracepath.read_bytes()))
        if (game['status'] != 'DONE' or game['calls'] != 719 or game['errors'] or game['parity_pass'] is not True
                or game['backend'] != 'official' or len(trace['actions']) != 719 or sha(tracepath) != game['trace']['sha256']):
            raise RuntimeError('SOURCE_GAME_NOT_QUALIFIED_FOR_REPRODUCTION')
        if game['key'] != freeze['source_game_key'] or game['seed'] != freeze['seed'] or game['candidate_seat'] != freeze['seat']:
            raise RuntimeError('SOURCE_KEY_CHANGED')
        h = load_module('budget_original_harness', manifest['harness']['path'])
        if h.digest(manifest) != game['manifest_sha256']:
            raise RuntimeError('GAME_MANIFEST_MISMATCH')
        for name in ('candidate', 'opponent', 'engine'):
            h.check_files(manifest[name])
        param_env = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in os.environ.items() if k in {'V15_PARAMS', 'V125_PARAMS'}}
        if param_env != manifest['agent_parameter_environment_sha256']:
            raise RuntimeError('SOURCE_PARAMETER_ENV_MISMATCH')
        make, rules, fast, engine_info = h.import_engines()
        if engine_info['composite_sha256'] != manifest['engine']['composite_sha256']:
            raise RuntimeError('ENGINE_COMPOSITE_CHANGED')
        dump(out / 'audit_manifest.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(),
             'freeze_path': str(args.freeze.resolve()), 'freeze_sha256': guards[str(args.freeze.resolve())],
             'guarded_files': guards, 'source_game_key': game['key'],
             'requested_candidate_calls': 719, 'requested_saved_action_engine_steps': 719, 'new_independent_matches': 0,
             'profile_performance_role': 'EXCLUDED_FROM_G0_AND_PERFORMANCE_EVIDENCE'})
        engine = h.Engine('official', trace['seed'], make, fast)
        seat = game['candidate_seat']
        agent = h.Agent(manifest['candidate'], trace['seed'], seat)
        codes = [c for c in agent.module.economic_plan_prefix.__code__.co_consts if isinstance(c, types.CodeType) and c.co_name == 'budget_quote']
        if len(codes) != 1 or codes[0].co_firstlineno != freeze['budget_quote_first_line']:
            raise RuntimeError('EXACT_QUOTE_CODE_OBJECT_NOT_FOUND')
        profiler = BudgetProfiler(codes[0], {int(k): v for k, v in freeze['callsites'].items()})
        cfg = h.agent_configuration(manifest, engine)
        if cfg != manifest['configuration'] or cfg.get('seed') is not None:
            raise RuntimeError('AGENT_CONFIGURATION_CHANGED')
        original_diagnostics = game['strategy_diagnostics'][seat]
        receipts = original_diagnostics[str(seat)]['investment_receipts']
        if len(receipts) != 719 or [r['step'] for r in receipts] != list(range(719)):
            raise RuntimeError('INCOMPLETE_SOURCE_RECEIPTS')
        daily = {rows[0]['step']: [{k: v for k, v in r.items() if k != 'audit_cumulative'} for r in rows] for rows in game['daily']}
        if len(daily) != len(game['daily']):
            raise RuntimeError('DUPLICATE_SNAPSHOT_STEP')
        for step, pair in enumerate(trace['actions']):
            observations = [engine.observe(s) for s in (0, 1)]
            obs = observations[seat]
            if obs['step'] != step or engine.done() or 'seed' in obs:
                raise RuntimeError(f'UNEXPECTED_OBSERVATION step={step}')
            if step in daily:
                if plain(h.snapshot(observations)) != daily[step]:
                    raise RuntimeError(f'SOURCE_SNAPSHOT_MISMATCH step={step}')
                snapshots_checked += 1
            before = contract_summary(agent.module._STATES.get(seat, {}))
            profiler.begin(step)
            oldprofile = sys.getprofile()
            calls += 1
            sys.setprofile(profiler.profile)
            try:
                action = agent.call(obs, copy.deepcopy(cfg), 10)
            finally:
                sys.setprofile(oldprofile)
            all_rows.extend(profiler.rows)
            difference = h.first_difference(plain(action), pair[seat])
            if difference:
                raise RuntimeError(f'ACTION_MISMATCH step={step}: {difference}')
            compared += 1
            observed_rejections = {k: v for k, v in profiler.counts.items() if k != 'accepted_quote'}
            own_receipt = agent.module._STATES[seat]['investment_receipts'][-1]
            if observed_rejections != receipts[step]['rejected_types'] or observed_rejections != own_receipt['rejected_types']:
                raise RuntimeError(f'REJECTION_COUNTS_MISMATCH step={step}: {observed_rejections} expected={receipts[step]["rejected_types"]}')
            difference = h.first_difference(plain(own_receipt), receipts[step])
            if difference:
                raise RuntimeError(f'RECEIPT_MISMATCH step={step}: {difference}')
            receipts_checked += 1
            reason_totals.update(observed_rejections)
            step_rows.append({'step': step, 'day': obs['day'], 'hour': obs['hour'], 'actual_cash': obs['farms'][seat]['money'],
                'actual_hands': len(obs['farms'][seat]['hands']), 'counts': dict(profiler.counts),
                'contracts_before_call': before, 'contracts_after_call': contract_summary(agent.module._STATES[seat]),
                'action': plain(action), 'chosen_expert': own_receipt['expert'], 'accepted_quotes': own_receipt['admitted'],
                'source_receipt_equal': True})
            engine.step(copy.deepcopy(pair))
            steps += 1
            if steps % 120 == 0:
                print(json.dumps({'completed_saved_steps': steps, 'candidate_calls': calls, 'labor_rejections_so_far': reason_totals['labor']}), flush=True)
        terminal = plain(h.snapshot([engine.observe(s) for s in (0, 1)]))
        if not engine.done() or engine.statuses() != ['DONE', 'DONE'] or engine.rewards() != game['rewards'] or terminal != game['terminal']:
            raise RuntimeError('TERMINAL_MISMATCH')
        if terminal != daily[719]:
            raise RuntimeError('TERMINAL_DAILY_SNAPSHOT_MISMATCH')
        snapshots_checked += 1
        diagnostics = plain(agent.diagnostics())
        difference = h.first_difference(diagnostics, original_diagnostics)
        dump(out / 'diagnostics_comparison.json', {'equal_all_fields_after_same_json_representation': difference is None,
              'first_difference': difference, 'reproduced_sha256': hashlib.sha256(json.dumps(diagnostics, sort_keys=True).encode()).hexdigest(),
              'source_sha256': hashlib.sha256(json.dumps(original_diagnostics, sort_keys=True).encode()).hexdigest()})
        if difference:
            raise RuntimeError(f'DIAGNOSTICS_MISMATCH {difference}')
        expected_totals = sum((collections.Counter(r['rejected_types']) for r in receipts), collections.Counter())
        if reason_totals != expected_totals or sum(reason_totals.values()) != original_diagnostics[str(seat)]['metrics']['investment_budget_rejected_quotes']:
            raise RuntimeError('TOTAL_REJECTIONS_MISMATCH')
        for path, expected in guards.items():
            if sha(path) != expected:
                raise RuntimeError(f'GUARDED_FILE_CHANGED_AFTER_REPRODUCTION {path}')
        summary = aggregate(all_rows)
        summary.update(status='DIAGNOSTIC_COMPLETE', source_game_key=game['key'], candidate_calls=calls,
              saved_action_engine_steps=steps, new_independent_matches=0, opponent_candidate_calls=0,
              action_comparisons=compared, per_frame_receipts_compared=receipts_checked, saved_snapshots_compared=snapshots_checked,
              diagnostics_equal_source=True, terminal_equal_source=True, cash=engine.rewards(),
              rejection_totals=dict(reason_totals), all_source_shas_unchanged=True,
              count_closure='逐帧profile拒绝数=本次原receipt=原局保存receipt；全部719receipt及终态diagnostics全字段一致',
              quote_samples=list(profiler.samples.values()), performance_evidence=False,
              qualification='同一已打开局的内部模型诊断；无新比赛、无G1/G2/Gold裁决')
        dump(out / 'summary.json', summary)
    except Exception as exc:
        failure = {'error': f'{type(exc).__name__}: {exc}', 'traceback': traceback.format_exc(), 'candidate_calls': calls,
                   'saved_action_engine_steps': steps, 'actions_compared': compared, 'receipts_compared': receipts_checked,
                   'new_independent_matches': 0}
        if profiler is not None:
            failure.update(last_step=profiler.step, last_counts=dict(profiler.counts))
        dump(out / 'failure.json', failure)
    finally:
        if profiler is not None and profiler.rows and (not all_rows or all_rows[-1]['step'] != profiler.step):
            all_rows.extend(profiler.rows)
        for name, rows in [('labor_rejections', all_rows), ('step_context', step_rows)]:
            with gzip.open(out / (name + '.jsonl.gz'), 'wt') as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n')
        changed = [path for path, expected in guards.items() if not Path(path).is_file() or sha(path) != expected]
        if changed:
            failure = {**(failure or {}), 'error': 'GUARDED_FILES_CHANGED', 'changed_paths': changed,
                       'candidate_calls': calls, 'saved_action_engine_steps': steps, 'new_independent_matches': 0}
            dump(out / 'failure.json', failure)
    if failure:
        raise RuntimeError(failure['error'])
    dump(out / 'validation.json', {'status': 'COMPLETE', 'all_source_files_unchanged': True,
         'candidate_calls': calls, 'saved_action_engine_steps': steps, 'new_independent_matches': 0,
         'files': {str(p.resolve()): sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps({'status': 'DIAGNOSTIC_COMPLETE', 'candidate_calls': calls, 'saved_action_engine_steps': steps,
         'labor_rejections': len(all_rows), 'output': str(out)}, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
