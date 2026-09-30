"""R10 经济接入静态辅助函数；仅供构建，不直接作为推理包。"""
import copy as _r10_integration_copy


def _r10_integration_rescue_key(obs, item, pos):
    tile = obs['farms'][obs['player']]['tiles'][pos[1]][pos[0]]
    kind = tile.get('kind', 'UNKNOWN') if isinstance(tile, dict) else 'EMPTY' if tile is None else str(tile)
    return '%d|%s|%d|%d|%s' % (obs['player'], item, pos[0], pos[1], kind)


def _r10_integration_rescue_cycle(st, obs):
    cycles = st.setdefault('_r10_rescue_cycles', {})
    seat = str(obs['player'])
    cycle = cycles.get(seat)
    if cycle is None:
        cycle = {'seat': obs['player'], 'index': 0, 'failed_keys': [],
                 'reset_after_step': None, 'last_attempt_step': None}
        cycles[seat] = cycle
    return cycle


def _r10_integration_select_rescue(st, obs, offers):
    cycle = _r10_integration_rescue_cycle(st, obs)
    if cycle['last_attempt_step'] == obs['step']:
        return {'q': None, 'cycle': cycle, 'status': 'ALREADY_ATTEMPTED_THIS_FRAME'}
    if not offers:
        return {'q': None, 'cycle': cycle, 'status': 'NO_ELIGIBLE_RESCUE'}
    failed = set(cycle['failed_keys'])
    untried = [q for q in offers if q['_r10_rescue_key'] not in failed]
    if untried:
        # 即使上一帧刚耗尽，新的未试项目仍先于旧失败项目。
        cycle['reset_after_step'] = None
    elif cycle['reset_after_step'] is not None and obs['step'] > cycle['reset_after_step']:
        cycle['failed_keys'] = []
        cycle['reset_after_step'] = None
        cycle['index'] += 1
        untried = offers
    else:
        cycle['reset_after_step'] = obs['step']
        return {'q': None, 'cycle': cycle, 'status': 'FAILED_CYCLE_EXHAUSTED_RESET_NEXT_FRAME'}
    q = min(untried, key=lambda q: (-q['selection_score'],
        dist(q['position'], home(q['position'])), q['position']))
    cycle['last_attempt_step'] = obs['step']
    return {'q': q, 'cycle': cycle, 'status': 'SELECTED_UNCERTIFIED_RESCUE'}


def _r10_integration_fail_rescue(cycle, obs, key, eligible_keys):
    failed = set(cycle['failed_keys'])
    failed.add(key)
    cycle['failed_keys'] = sorted(failed)
    if eligible_keys and all(k in failed for k in eligible_keys):
        cycle['reset_after_step'] = obs['step']


def _r10_integration_new_context(obs, model):
    token = 'step%d-seat%d' % (obs['step'], obs['player'])
    return {'obs': obs, 'model': model, 'token': token, 'sources': [], 'compiled': {},
            'actual': None, 'cache': _r10_route_admission_PlanRouteCache(token, obs['day'], obs['private'],
                evidence_mode='production_compact_v1'),
            'counts': {}, 'reasons': {}, 'first_events': [], 'last_accepted_proof': None,
            'unrepresented_commitments': []}


def _r10_integration_increment(ctx, key, value=1):
    ctx['counts'][key] = ctx['counts'].get(key, 0) + value


def _r10_integration_register_quote(ctx, q):
    # 与原 workload 累加同位置登记；不因同一 q 同时在 transit/commitment 列表而重复。
    ctx['sources'].append(q)
    ctx['last_accepted_proof'] = q.get('_r10_approval')


def _r10_integration_note_unrepresented_commitment(ctx, contract, item, pos):
    ctx['unrepresented_commitments'].append({'target': list(pos), 'item': item,
        'remaining_stages': _r10_integration_copy.deepcopy(contract.get('stages', [])),
        'reason': 'ORIGINAL_COMMITTED_QUOTE_NONE'})


def _r10_integration_legacy_equal(original, compiled):
    return all(original[k] == compiled[k] for k in ('goods', 'work', 'feed'))


def _r10_integration_actual_calendars(ctx):
    if ctx['actual'] is not None:
        return ctx['actual']
    obs = ctx['obs']
    expected = {(x, y): tile for y, row in enumerate(obs['farms'][obs['player']]['tiles'])
                for x, tile in enumerate(row) if isinstance(tile, dict) and
                (tile.get('kind') == 'PLANT' or 'animal' in tile)}
    old = {}
    for seat, pos, calendar in ctx['model']['calendars']:
        if seat != obs['player']:
            continue
        pos = tuple(pos)
        _r10_route_admission__need(pos not in old, 'DUPLICATE_OBSERVED_MODEL_POSITION')
        old[pos] = calendar
    _r10_route_admission__need(set(expected) == set(old), 'OBSERVED_MODEL_ASSET_COVERAGE')
    rows = []
    for pos, tile in sorted(expected.items()):
        calendar = _r10_calendar_compiler_project_calendar_with_services(tile, obs['day'], obs['hour'], pos,
            {'kind': 'actual_observed_field_asset', 'observation_step': obs['step'], 'position': list(pos)})
        _r10_integration_increment(ctx, 'actual_calendar_compilations')
        _r10_route_admission__need(_r10_integration_legacy_equal(old[pos], calendar), 'OBSERVED_LEGACY_CALENDAR_MISMATCH')
        rows.append((calendar, old[pos], None))
    ctx['actual'] = rows
    return rows


def _r10_integration_quote_calendar(ctx, q):
    material = {key: q[key] for key in ('item', 'position', 'start_step_model', 'setup_work', 'calendar', 'fixed_cash')}
    key = _r10_calendar_compiler_canonical_sha(material)
    if key in ctx['compiled']:
        _r10_integration_increment(ctx, 'quote_calendar_cache_hits')
        return ctx['compiled'][key]
    item, start = q['item'], q['start_step_model']
    _r10_route_admission__need(type(start) is int and ctx['obs']['step'] <= start < 718,
                              'INVALID_QUOTE_START_STEP')
    day, hour = start // 24, start % 24 + 1
    if item in ANIMALS:
        future = {'kind': ANIMALS[item][1], 'animal': item, 'placed_day': day, 'yield_units': 0,
                  'fed_today': False, 'cared_today': False, 'fertilizer_available': False, 'pending_care_bonus': 0}
    else:
        _r10_route_admission__need(item in CROPS, 'UNKNOWN_QUOTE_ITEM')
        future = {'kind': 'PLANT', 'crop': item, 'planted_day': day,
                  'yield_units': 0 if CROPS[item][3] else 1, 'watered_today': False,
                  'consecutive_unwatered': 1, 'fertilized_until_day': -1}
    cal = _r10_calendar_compiler_project_calendar_with_services(future, day, hour, q['position'],
        {'kind': 'conditional_quote_asset', 'model_start_step': start, 'item': item,
         'fixed_cash_model': q['fixed_cash'], 'actual_observation_proven': False})
    for d, n in q['setup_work'].items():
        _r10_route_admission__need(type(d) is int and ctx['obs']['day'] <= d <= 29 and type(n) is int and n >= 0,
                                  'INVALID_QUOTE_SETUP_WORK')
        cal['work'][d] = cal['work'].get(d, 0) + n
    _r10_route_admission__need(_r10_integration_legacy_equal(q['calendar'], cal), 'QUOTE_LEGACY_CALENDAR_MISMATCH')
    _r10_integration_increment(ctx, 'quote_calendar_compilations')
    # 只是不可变纯编译结果；不是已许可项目，也不进入 source registry。
    ctx['compiled'][key] = cal
    return cal


def _r10_integration_rows(ctx, trial_q=None):
    _r10_route_admission__need(not ctx['unrepresented_commitments'], 'UNREPRESENTED_COMMITMENT_WITHOUT_CALENDAR')
    rows = list(_r10_integration_actual_calendars(ctx))
    sources = list(ctx['sources']) + ([trial_q] if trial_q is not None else [])
    for q in sources:
        rows.append((_r10_integration_quote_calendar(ctx, q), q['calendar'], q))
    owned = {a: inventory_total(ctx['obs']['private'], a) for a in ANIMALS}
    assigned = {a: 0 for a in ANIMALS}
    for _, _, q in rows:
        if q is not None and q['item'] in ANIMALS and q['fixed_cash'] == 0:
            assigned[q['item']] += 1
    _r10_route_admission__need(owned == assigned, 'UNASSIGNED_IN_TRANSIT_WITHOUT_CALENDAR')
    return rows


def _r10_integration_portfolio(ctx, rows, workload, labor, requirements, book):
    today = ctx['obs']['day']
    work, feed, goods = {}, {}, {}
    startup = set()
    pending = {}
    for _, old, q in rows:
        for key, target in (('work', work), ('feed', feed)):
            for day, qty in old[key].items():
                target[day] = target.get(day, 0) + qty
        for day, products in old['goods'].items():
            row = goods.setdefault(day, {})
            for item, qty in products.items():
                row[item] = row.get(item, 0) + qty
        if q is not None:
            startup.update(day for day, qty in q['setup_work'].items() if qty)
            startup.add(q['start_step_model'] // 24)
            if q['item'] in ANIMALS and q['fixed_cash'] > 0:
                pending[q['item']] = pending.get(q['item'], 0) + 1
    funding = {'buys_by_day': dict(book['feed_buys_by_day']),
               'stock_by_day': dict(book['feed_ending_stock_by_day']),
               'cash_by_day': dict(book['feed_cash_by_day']),
               'total_cash': sum(book['feed_cash_by_day'].values())}
    return {'calendars': [c for c, _, _ in rows], 'coverage_asset_ids': [c['asset_id'] for c, _, _ in rows],
            'legacy_aggregate': {'goods': goods, 'work': work, 'feed': feed},
            'workload': dict(workload), 'labor': _r10_integration_copy.deepcopy(labor),
            'funding_requirements': {d: requirements.get(d, 0) for d in range(today, 30)},
            'funding_feed': funding, 'startup_fallback_days': sorted(startup), 'pending_animal_units': pending,
            'conditional_prior_product_sales': True}


def _r10_integration_compact_result(result):
    witnesses = []
    for day in result.get('day_evidence', []):
        stats = day['conditional_result']
        witnesses.append({key: day[key] for key in ('day', 'problem_sha256', 'old_need', 'old_capacity',
            'old_hire_cash', 'buffer_debit', 'start_shed', 'reserved_shed', 'buy')})
        witnesses[-1].update(service_count=stats['completed_service_count'],
            delivered_goods=stats['delivered_goods'], purchased_goods=stats['purchased_goods'],
            terminal_shed=stats['terminal_shed'])
    return {'status': result['status'], 'labor_feasible_after_routes': result['labor_feasible_after_routes'],
            'route_feasibility_by_day': dict(result.get('route_feasibility_by_day', {})),
            'reason': result.get('reason'), 'failed_day': result.get('failed_day'),
            'trial_legacy_sha256': result.get('trial_legacy_sha256'),
            'witnesses': witnesses, 'conditional_not_actual_execution': True}


def _r10_integration_try_route(ctx, q, workload, base_labor, next_work, labor,
                               funding_requirements, funding_book, trial_requirements, trial_book):
    _r10_integration_increment(ctx, 'route_attempts')
    before_sources = len(ctx['sources'])
    try:
        base_rows = _r10_integration_rows(ctx)
        trial_rows = _r10_integration_rows(ctx, q)
        baseline = _r10_integration_portfolio(ctx, base_rows, workload, base_labor, funding_requirements, funding_book)
        trial = _r10_integration_portfolio(ctx, trial_rows, next_work, labor, trial_requirements, trial_book)
        result = _r10_route_admission_route_admission(baseline, trial, current_day=ctx['obs']['day'],
            observed_private=ctx['obs']['private'], plan_token=ctx['token'], cache=ctx['cache'],
            implementation_ids=_r10_integration_IMPLEMENTATION_IDS, evidence_mode='production_compact_v1')
    except (_r10_route_admission_BindingError, KeyError, TypeError, ValueError) as exc:
        result = {'status': 'BINDING_REJECTED', 'labor_feasible_after_routes': False, 'reason': str(exc),
                  'failed_day': None, 'scheduler_calls': 0, 'checker_calls': 0, 'cache_hits': 0}
    _r10_route_admission__need(len(ctx['sources']) == before_sources, 'TRIAL_CHANGED_BASELINE_SOURCES')
    for key in ('scheduler_calls', 'checker_calls', 'cache_hits'):
        _r10_integration_increment(ctx, key, result.get(key, 0))
    _r10_integration_increment(ctx, 'route_successful_quotes' if result['labor_feasible_after_routes'] else 'route_failed_quotes')
    compact = _r10_integration_compact_result(result)
    q['_r10_approval'] = compact
    reason = (result.get('reason') or result['status']).split(':', 1)[0]
    ctx['reasons'][reason] = ctx['reasons'].get(reason, 0) + 1
    if len(ctx['first_events']) < 16:
        ctx['first_events'].append({'item': q['item'], 'position': list(q['position']), 'status': result['status'],
            'failed_day': result.get('failed_day'), 'reason': result.get('reason'),
            'route_days': sorted(result.get('route_feasibility_by_day', {}))})
    return result['labor_feasible_after_routes']


def _r10_integration_finish(ctx, plan, receipt):
    proof = ctx['last_accepted_proof']
    route_days = dict(proof['route_feasibility_by_day']) if proof else {}
    today = ctx['obs']['day']
    failures = [d for d in range(today, 30) if plan['planned_work'].get(d, 0) > plan['labor_plan']['capacity_by_day'][d]]
    effective = not failures or all(d > today and route_days.get(d) for d in failures)
    plan['r10_route_feasibility_by_day'] = route_days
    plan['r10_effective_labor_feasible'] = bool(effective)
    receipt['r10_future_route'] = {'mode': 'bounded_future_failure_rescue', 'counts': dict(ctx['counts']),
        'reason_counts': dict(ctx['reasons']), 'first_events': list(ctx['first_events']),
        'event_detail_limit': 16, 'events_are_quote_attempts_not_actual_permits': True,
        'final_legacy_failed_days': failures, 'final_effective_labor_feasible': bool(effective),
        'last_accepted_proof': proof, 'source_quote_count': len(ctx['sources']),
        'compiled_quote_cache_entries': len(ctx['compiled']), 'route_cache_entries': len(ctx['cache'].entries),
        'unrepresented_commitments': _r10_integration_copy.deepcopy(ctx['unrepresented_commitments']),
        'cost_and_three_score_formulas_unchanged': True, 'cheap_phase_policy': 'original_r9',
        'rescue_changes_admission': True, 'prior_product_sales_are_conditional': True}
