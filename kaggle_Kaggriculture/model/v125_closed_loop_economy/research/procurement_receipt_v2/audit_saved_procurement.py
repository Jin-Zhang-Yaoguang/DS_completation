#!/usr/bin/env python3
"""只解析已存官方事件/捕获；不导入策略或引擎，不重放动作。"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path

ANIMALS = ('COW', 'SHEEP', 'GOOSE')
PURCHASES = {'BUY_SEED', 'BUY_ANIMAL', 'BUY_PRODUCT', 'BUY_LAND', 'HIRE'}
EVENT_OPS = {'BUY_SEED', 'BUY_ANIMAL', 'BUY_PRODUCT', 'SELL'}
FROZEN_ANALYZER = 'cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Inputs:
    def __init__(self):
        self.files = {}

    def capture_bytes(self, path, expected=None):
        path = Path(path).resolve()
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if expected is not None and actual != expected:
            raise ValueError('INPUT_SHA_MISMATCH: ' + str(path))
        if str(path) in self.files and actual != self.files[str(path)]:
            raise ValueError('INPUT_CHANGED_DURING_AUDIT: ' + str(path))
        self.files.setdefault(str(path), actual)
        return data

    def load(self, path, expected=None, lines=False):
        data = self.capture_bytes(path, expected)
        if Path(path).suffix == '.gz': data = gzip.decompress(data)
        source = data.decode('utf-8')
        def invalid_constant(value): raise ValueError('NONFINITE_JSON:' + value)
        if lines:
            return [json.loads(line, parse_constant=invalid_constant) for line in source.splitlines() if line.strip()]
        return json.loads(source, parse_constant=invalid_constant)

    def recheck(self):
        for path, expected in self.files.items():
            if sha(path) != expected:
                raise ValueError('INPUT_CHANGED_BEFORE_OUTPUT: ' + path)


def require_integer(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError('INVALID_INTEGER_DOMAIN:' + label)
    return value


def require_money(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError('INVALID_MONEY_DOMAIN:' + label)
    return value


def validate_market_events(events):
    for event in events:
        quantity = event.get('quantity')
        if isinstance(quantity, dict):
            for value in quantity.values(): require_integer(value, 'event.quantity.item')
        elif quantity is not None:
            require_integer(quantity, 'event.quantity', 1)
        for value in event.get('discarded', {}).values(): require_integer(value, 'event.discarded.item')
        if 'price' in event: require_money(event['price'], 'event.price')
        if event.get('kind') != 'market': continue
        require_integer(event['quantity'], 'event.quantity', 1)
        require_money(event['price'], 'event.price')
        require_integer(event['decision_step'], 'event.decision_step')
        require_integer(event['seat'], 'event.seat')
        if event['decision_step'] > 718 or event['seat'] not in (0, 1):
            raise ValueError('EVENT_OUTSIDE_GAME')


def identity(order):
    op = order[0]
    item = order[1] if len(order) > 1 else ('land' if op == 'BUY_LAND' else 'hands')
    if op in ('BUY_LAND', 'HIRE'):
        quantity = 1
    else:
        if len(order) < 3: raise ValueError('MISSING_ORDER_QUANTITY')
        quantity = require_integer(order[2], 'order.quantity', 1)
    return op, item, quantity


def requests(trace, seat):
    rows = []
    for step, pair in enumerate(trace['actions']):
        market = pair[seat].get('market', [])
        for index, order in enumerate(market):
            if order and order[0] in PURCHASES:
                op, item, n = identity(order)
                rows.append({'step': step, 'seat': seat, 'order_index': index,
                             'order': order, 'op': op, 'item': item, 'requested': n,
                             'outside_ten_order_limit': index >= 10})
    return rows


def group_events(events, seat):
    validate_market_events(events)
    groups = defaultdict(list)
    for event in events:
        if event['kind'] == 'market' and event['seat'] == seat:
            groups[(event['decision_step'], event['op'], event['item'])].append(event)
    return groups


def match_events(request_rows, events, seat, complete):
    """缺订单索引时只接受唯一(op,item)映射；不猜逐单位成交属于哪笔。"""
    groups = group_events(events, seat)
    counts = Counter((r['step'], r['op'], r['item']) for r in request_rows if not r['outside_ten_order_limit'])
    result = []
    for req in request_rows:
        row = dict(req)
        key = (req['step'], req['op'], req['item'])
        if req['outside_ten_order_limit']:
            status = 'PENDING_OUTSIDE_ORDER_LIMIT'
        elif req['op'] not in EVENT_OPS:
            status = 'PENDING_ATOMIC_EVENT_NOT_RECORDED'
        elif not complete:
            status = 'PENDING_EVENT_COVERAGE'
        elif counts[key] != 1:
            status = 'PENDING_DUPLICATE_SAME_ITEM_ORDER'
        else:
            status = 'PASS'
        if status == 'PASS':
            units = groups.get(key, [])
            qty = sum(z['quantity'] for z in units)
            row.update(actual_quantity=qty, actual_cash=sum(z['quantity'] * z['price'] for z in units),
                       actual_unit_prices=[z['price'] for z in units for _ in range(z['quantity'])])
            if qty > req['requested']:
                status = 'FAIL_EVENT_QUANTITY_OVER_REQUEST'
        else:
            row.update(actual_quantity=None, actual_cash=None, actual_unit_prices=None)
        row['actual_status'] = status
        row['inventory_status'] = 'PENDING_NO_PER_FRAME_OBSERVATIONS'
        row['confirmation_status'] = 'EXTERNAL_TERMINAL_ONLY' if req['step'] == 718 else 'PENDING_ORIGINAL_CONFIRM_CAPTURE'
        row['target_status'] = 'PENDING_TARGET_EVIDENCE'
        row['cash_intent_status'] = 'PENDING_CASH_INTENT_EVIDENCE'
        result.append(row)
    return result


def liquid(private):
    result = Counter(private['shed'])
    for inv in private['inventories']:
        result.update(inv)
    return result


def field_animals(farm):
    return Counter(t['animal'] for row in farm['tiles'] for t in row if isinstance(t, dict) and t.get('animal'))


def snapshot_intervals(daily, events, seat):
    """仅有日快照时核区间物量；不把它冒充每笔采购帧的闭合。"""
    results = []
    for left, right in zip(daily, daily[1:]):
        start, end = left['recorded_step'], right['recorded_step']
        before, after = left['states'][seat], right['states'][seat]
        if before['step'] != start or after['step'] != end or end <= start:
            raise ValueError('INVALID_OBSERVATION_INTERVAL')
        es = [z for z in events if z['seat'] == seat and start <= z['decision_step'] < end]
        planted = Counter(z['crop'] for z in es if z['kind'] == 'plant')
        seed_buys = Counter()
        animal_buys, placed, losses = Counter(), Counter(), Counter()
        for z in es:
            if z['kind'] == 'market' and z['op'] == 'BUY_SEED': seed_buys[z['item']] += z['quantity']
            if z['kind'] == 'market' and z['op'] == 'BUY_ANIMAL': animal_buys[z['item']] += z['quantity']
            if z['kind'] == 'place_animal': placed[z['animal']] += 1
            if z['kind'] == 'eod_animal_escape': losses[z['animal']] += 1
            if z['kind'] == 'eod_inventory_drop':
                for animal in ANIMALS: losses[animal] += z['discarded'].get(animal, 0)
            if z['kind'] == 'manual_drop_overflow':
                for animal in ANIMALS: losses[animal] += z['quantity'].get(animal, 0)
        bp, ap = before['private'], after['private']
        seeds = set(bp['seeds']) | set(ap['seeds']) | set(seed_buys) | set(planted)
        seed_residuals = {p: bp['seeds'].get(p, 0) + seed_buys[p] - planted[p] - ap['seeds'].get(p, 0) for p in sorted(seeds)}
        bl, al = liquid(bp), liquid(ap)
        bf, af = field_animals(before['farms'][seat]), field_animals(after['farms'][seat])
        total_residuals = {p: bl[p] + bf[p] + animal_buys[p] - losses[p] - al[p] - af[p] for p in ANIMALS}
        # 未放动物库存损失不含在田逃逸；PLACE在总资产账抵消，在库存子账扣减。
        liquid_loss = Counter()
        for z in es:
            lost = z.get('discarded', {}) if z['kind'] == 'eod_inventory_drop' else z.get('quantity', {}) if z['kind'] == 'manual_drop_overflow' else {}
            if isinstance(lost, dict):
                for p in ANIMALS: liquid_loss[p] += lost.get(p, 0)
        liquid_residuals = {p: bl[p] + animal_buys[p] - placed[p] - liquid_loss[p] - al[p] for p in ANIMALS}
        results.append({'start_observation_step': start, 'end_observation_step': end,
                        'seed_residuals': seed_residuals, 'total_animal_residuals': total_residuals,
                        'unplaced_animal_residuals': liquid_residuals,
                        'status': 'PASS' if all(v == 0 for d in (seed_residuals, total_residuals, liquid_residuals) for v in d.values()) else 'FAIL'})
    return results


def validate_trace(trace, game, seat):
    if game['status'] != 'DONE' or game['calls'] != 719 or len(trace['actions']) != 719:
        raise ValueError('SOURCE_NOT_COMPLETE_719')
    if trace['seed'] != game['seed'] or trace['candidate_seat'] != seat or game['candidate_seat'] != seat:
        raise ValueError('SOURCE_IDENTITY_MISMATCH')


def audit_mechanism(root, inputs):
    validation = inputs.load(root / 'validation.json')
    def artifact(name):
        if name not in validation['files']: raise ValueError('UNREGISTERED_ARTIFACT:' + name)
        return inputs.load(root / name, validation['files'][name], name.endswith('.jsonl.gz'))
    manifest = artifact('audit_manifest.json')
    if manifest['analyzer']['sha256'] != FROZEN_ANALYZER:
        raise ValueError('UNREVIEWED_ANALYZER')
    inputs.capture_bytes(manifest['analyzer']['path'], FROZEN_ANALYZER)
    trace = inputs.load(manifest['source_trace']['path'], manifest['source_trace']['sha256'])
    games = inputs.load(manifest['source_games']['path'], manifest['source_games']['sha256'], True)
    game = games[manifest['source_games']['game_index']]
    seat = manifest['candidate_seat']
    validate_trace(trace, game, seat)
    events, daily = artifact('events.jsonl.gz'), artifact('daily_states.json.gz')
    validate_market_events(events)
    complete = all(validation.get(k) is True for k in ('source_trace_sha_verified', 'terminal_full_snapshot_matches_source', 'actual_market_quantities_match_source')) and validation.get('saved_actions_replayed') == 719
    totals = defaultdict(Counter)
    for e in events:
        if e['kind'] == 'market' and e['seat'] == seat:
            totals[e['op'] + '_qty'][e['item']] += e['quantity']
            totals[e['op'] + '_cash'][e['item']] += e['quantity'] * e['price']
    actual = game['action_audit']['actual_market_ledger'][seat]
    for op in EVENT_OPS:
        for suffix in ('_qty', '_cash'):
            if dict(totals[op + suffix]) != actual.get(op + suffix, {}):
                raise ValueError('OFFICIAL_TOTAL_MISMATCH:' + op + suffix)
    return {'mode': 'FROZEN_ANALYZE_TRACE_EVENTS', 'source_game_key': game['key'],
            'orders': match_events(requests(trace, seat), events, seat, complete),
            'observation_intervals': snapshot_intervals(daily, events, seat),
            'first_available_observation_step': daily[0]['recorded_step'],
            'initial_interval_pending': daily[0]['recorded_step'] != 0,
            'actual_market_qty_and_cash_match_saved_game': True,
            'scope': '原子订单/逐帧状态/原确认/目标合同不足部分分别PENDING；日区间闭合不代替逐笔证明。'}


def audit_capture(root, inputs):
    """读旧R0/R4的额外逐笔捕获，不执行任何观察器或策略。"""
    validation = inputs.load(root / 'validation.json')
    def artifact(name):
        if name not in validation['files']: raise ValueError('UNREGISTERED_ARTIFACT:' + name)
        return inputs.load(root / name, validation['files'][name], name.endswith('.jsonl.gz'))
    manifest = artifact('audit_manifest.json')
    trace = inputs.load(manifest['source_trace']['path'], manifest['source_trace']['sha256'])
    games = inputs.load(Path(manifest['source_run']) / 'games.jsonl', manifest['source_games_sha256'], True)
    game = games[manifest['source_game_index']]; seat = game['candidate_seat']
    validate_trace(trace, game, seat)
    commits = artifact('official_unit_commits.jsonl.gz')
    plants = artifact('official_plant_consumption.jsonl.gz')
    escapes = artifact('official_animal_escapes.jsonl.gz')
    overflow = artifact('official_animal_overflow.jsonl.gz')
    frames = artifact('external_state_frames.jsonl.gz')
    proposals = artifact('candidate_fixed_order_calls.jsonl.gz')
    confirms = artifact('candidate_original_checks.jsonl.gz')
    for z in plants:
        for value in z['consumed'].values(): require_integer(value, 'plant.consumed')
    for z in overflow: require_integer(z['quantity'], 'overflow.quantity')
    if [f['step'] for f in frames] != list(range(719)): raise ValueError('FRAME_COVERAGE_MISMATCH')
    actual, original, targets = defaultdict(list), defaultdict(list), defaultdict(list)
    for z in commits:
        quantity = require_integer(z['quantity'], 'commit.quantity')
        if quantity > 1: raise ValueError('NOT_A_PER_UNIT_COMMIT')
        if 'price' in z: require_money(z['price'], 'commit.price')
        delta = z['money_delta']
        if isinstance(delta, bool) or not isinstance(delta, (int, float)) or not math.isfinite(delta):
            raise ValueError('INVALID_COMMIT_CASH_DELTA')
        if z['op'] in PURCHASES and delta > 0: raise ValueError('PURCHASE_CASH_DELTA_POSITIVE')
        if 'price' in z and z['op'] in PURCHASES and abs(delta + z['price'] * quantity) > 1e-7:
            raise ValueError('COMMIT_CASH_PRICE_IDENTITY')
        actual[(z['step'], z['seat'], z['order_index'])].append(z)
    for z in confirms: original[(z['issued_step'], z['order_index'])].append(z)
    for z in proposals:
        if z['accepted_by_original_budget_check']: targets[(z['step'], z['orders_before'])].append(z)
    cash_chain = {}
    for step in range(719):
        cash = frames[step]['before']['money']
        chain_valid = True
        for z in (p for p in proposals if p['step'] == step):
            okay = chain_valid and abs(cash - z['cash_before']) < 1e-7
            if z['accepted_by_original_budget_check']:
                require_money(z['cost_budgeted'], 'proposal.cost_budgeted')
                require_money(z['cash_before'], 'proposal.cash_before')
                okay = okay and 0 <= z['cost_budgeted'] <= cash and z['order'] == trace['actions'][step][seat]['market'][z['orders_before']]
                cash -= z['cost_budgeted']
                cash_chain[(step, z['orders_before'])] = okay
            chain_valid = okay
    rows = []
    for req in requests(trace, seat):
        # 旧观察器原确认/土地证明范围，不把其余订单缺记录视为失败成交。
        if req['op'] not in ('BUY_SEED', 'BUY_ANIMAL', 'BUY_LAND'): continue
        row = dict(req); step, index, item, op = req['step'], req['order_index'], req['item'], req['op']
        cs = actual.get((step, seat, index), [])
        qty = sum(z['quantity'] for z in cs)
        row.update(actual_quantity=qty if cs else None,
                   actual_cash=-sum(z['money_delta'] for z in cs) if cs else None,
                   actual_unit_prices=[z.get('price', -z['money_delta'] / z['quantity']) if z['quantity'] else None for z in cs if z['quantity']],
                   actual_status='PASS' if cs and all(z['op'] == op and z['item'] == item for z in cs) and qty <= req['requested'] else 'PENDING_OR_INVALID_INDEXED_COMMIT')
        f = frames[step]; before, after = f['before'], f['after']
        used = sum(z['consumed'].get(item, 0) for z in plants if z['step'] == step and z['seat'] == seat)
        lost = sum(z['animal'] == item for z in escapes if z['step'] == step and z['seat'] == seat)
        lost += sum(z['quantity'] for z in overflow if z['step'] == step and z['seat'] == seat and z['animal'] == item)
        if op == 'BUY_SEED': delta = after['seeds'].get(item, 0) - before['seeds'].get(item, 0); corrected = delta + used
        elif op == 'BUY_ANIMAL': delta = after['assets'].get(item, 0) - before['assets'].get(item, 0); corrected = delta + lost
        else: delta = after['land'] - before['land']; corrected = delta
        group_qty = sum(z['quantity'] for z in commits if z['step'] == step and z['seat'] == seat and z['op'] == op and z['item'] == item)
        row.update(observed_net_change=delta, actual_seed_consumption=used, actual_animal_loss=lost,
                   corrected_frame_group_quantity=corrected, inventory_scope='FRAME_ITEM_GROUP',
                   inventory_status='PASS' if corrected == group_qty else 'FAIL_OBSERVATION_IDENTITY')
        cc = original.get((step, index), [])
        row['original_confirmation'] = cc[0] if len(cc) == 1 else None
        row['confirmation_status'] = 'EXTERNAL_TERMINAL_ONLY' if step == 718 else 'PENDING_ORIGINAL_CONFIRM_CAPTURE'
        if step < 718 and len(cc) == 1 and cc[0]['order'] == req['order'] and cc[0]['observed_step'] == step + 1:
            row['confirmation_status'] = 'PASS' if cc[0]['got_in_original_code'] == qty and cs else 'FAIL_ORIGINAL_CONFIRMATION'
        ts = targets.get((step, index), [])
        target = ts[0] if len(ts) == 1 else None
        row['target_capture'] = target
        gap = target.get('net_target_gap') if target else None
        row['target_status'] = 'PENDING_TARGET_EVIDENCE'
        if target and target.get('target') is not None and gap is not None and target['order'] == req['order']:
            observed_actual = before['assets'].get(item, 0) if op == 'BUY_ANIMAL' else before['seeds'].get(item, 0) if op == 'BUY_SEED' else before['land']
            if target.get('actual_before') != observed_actual or gap != max(0, target['target'] - observed_actual):
                row['target_status'] = 'FAIL_TARGET_NOT_CURRENT_OR_GAP_INCONSISTENT'
            else:
                row['target_status'] = 'PASS' if req['requested'] <= gap and qty <= gap else 'FAIL_OVER_TARGET'
        row['cash_intent_status'] = 'PASS' if cash_chain.get((step, index)) is True else 'PENDING_OR_INVALID_CASH_CHAIN'
        rows.append(row)
    return {'mode': 'SAVED_ORIGINAL_CAPTURE_SUPPLEMENT', 'source_game_key': game['key'], 'orders': rows,
            'observation_intervals': [], 'scope': '旧捕获仅核种子/动物/土地；目标是原局部目标或土地静态上限，不代表最优采购。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('mechanism', 'capture'), required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('REFUSE_OVERWRITE:' + str(args.output))
    inputs = Inputs()
    tool_sha = hashlib.sha256(inputs.capture_bytes(__file__)).hexdigest()
    result = (audit_mechanism if args.mode == 'mechanism' else audit_capture)(args.source.resolve(), inputs)
    result.update(created_at=datetime.now(timezone.utc).isoformat(), tool_sha256=tool_sha, inputs_sha256=inputs.files,
                  candidate_calls=0, engine_calls=0, new_complete_matches=0, formal_g1_status='PENDING_NOT_A_FORMAL_NEW_BLOCK')
    result['layer_counts'] = {key: dict(Counter(r[key] for r in result['orders'])) for key in
                              ('actual_status', 'inventory_status', 'confirmation_status', 'target_status', 'cash_intent_status')}
    output_bytes = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    inputs.recheck()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as out: out.write(output_bytes)
    print(json.dumps({'output': str(args.output), 'orders': len(result['orders']), 'layer_counts': result['layer_counts'],
                      'intervals': len(result['observation_intervals']), 'failed_intervals': sum(r['status'] != 'PASS' for r in result['observation_intervals'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
