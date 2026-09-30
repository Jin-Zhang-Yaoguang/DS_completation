#!/usr/bin/env python3
"""只读拆分已捕获未来失败；初报价/复查分别计量。"""
import collections, gzip, hashlib, json, math, statistics
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
HERE = BASE / 'v2'
SOURCE = BASE.parent / 'captured_r9_opened_s0'
ANIMALS = {'COW', 'SHEEP', 'GOOSE'}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dump(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def stats(values):
    a = sorted(values)
    if not a:
        return {'n': 0}
    return {'n': len(a), 'min': a[0], 'p10': a[max(0, math.ceil(.1 * len(a)) - 1)],
            'p25': a[max(0, math.ceil(.25 * len(a)) - 1)], 'median': statistics.median(a),
            'p75': a[max(0, math.ceil(.75 * len(a)) - 1)], 'p90': a[max(0, math.ceil(.9 * len(a)) - 1)],
            'p95': a[max(0, math.ceil(.95 * len(a)) - 1)], 'max': a[-1], 'mean': statistics.mean(a),
            'histogram': dict(sorted(collections.Counter(a).items()))}

def analyze(rows):
    first = [r['failure_days'][0] for r in rows]
    return {'attempts': len(rows), 'distinct_decision_steps': len({r['step'] for r in rows}),
            'distinct_step_item_position': len({(r['step'], r['item'], tuple(r['position'])) for r in rows}),
            'first_failure_deficit': stats([d['deficit'] for d in first]),
            'first_failure_offset': stats([r['first_failure_offset'] for r in rows]),
            'first_failure_day': dict(sorted(collections.Counter(r['first_failure_day'] for r in rows).items())),
            'first_failure_base_need': stats([d['base_need'] for d in first]),
            'first_failure_trial_need': stats([d['need'] for d in first]),
            'first_failure_base_capacity': stats([d['base_capacity'] for d in first]),
            'first_failure_trial_capacity': stats([d['capacity'] for d in first]),
            'first_failure_capacity_increase': stats([d['capacity'] - d['base_capacity'] for d in first]),
            'first_failure_capacity_unchanged_attempts': sum(d['capacity'] == d['base_capacity'] for d in first),
            'first_failure_capacity_increased_attempts': sum(d['capacity'] > d['base_capacity'] for d in first),
            'first_failure_baseline_headroom': stats([d['base_capacity'] - d['base_need'] for d in first]),
            'first_failure_added_work': stats([d['added_work'] for d in first]),
            'first_failure_quote_calendar_work': stats([d['quote_calendar_work'] for d in first]),
            'number_failed_days_per_attempt': stats([len(r['failure_days']) for r in rows]),
            'all_failed_days_deficit': stats([d['deficit'] for r in rows for d in r['failure_days']]),
            'baseline_infeasible_attempts': sum(r['baseline_already_infeasible'] for r in rows),
            'all_future_capacities_equal_baseline': all(d['capacity'] == d['base_capacity'] for r in rows for d in r['failure_days']),
            'first_failure_joint_histogram': [{'base_need': k[0], 'trial_need': k[1], 'capacity': k[2], 'attempts': n}
                for k, n in sorted(collections.Counter((d['base_need'], d['need'], d['capacity']) for d in first).items())]}

def main():
    HERE.mkdir(parents=True, exist_ok=True)
    if (HERE / 'analysis.json').exists():
        raise RuntimeError('REFUSE_EXISTING_ANALYSIS')
    validation = json.loads((SOURCE / 'validation.json').read_bytes())
    inputs = {**validation['files'], str(SOURCE / 'validation.json'): sha(SOURCE / 'validation.json'),
              str(BASE.parent / 'delivery_manifest.json'): sha(BASE.parent / 'delivery_manifest.json')}
    inputs[str(Path(__file__).resolve())] = sha(Path(__file__))
    for p, expected in inputs.items():
        assert sha(p) == expected, ('SOURCE_CHANGED', p)
    summary = json.loads((SOURCE / 'summary.json').read_bytes())
    assert summary['status'] == 'DIAGNOSTIC_COMPLETE'
    rows = [json.loads(line) for line in gzip.open(SOURCE / 'labor_rejections.jsonl.gz', 'rt')]
    selected = [r for r in rows if r['failure_class'] == 'future_only']
    groups = {phase: [r for r in selected if r['phase'] == phase] for phase in ('initial_offer', 'admission_recheck')}
    assert sum(map(len, groups.values())) == len(selected)
    for phase, part in groups.items():
        assert len({(r['step'], r['item'], tuple(r['position'])) for r in part}) == len(part), ('DUPLICATE_WITHIN_PHASE', phase)
    for r in selected:
        assert r['first_failure_offset'] > 0 and not r['baseline_already_infeasible']
        assert r['current_day']['trial_need'] <= r['current_day']['trial_capacity']
        assert r['funding_evaluation'] == 'NOT_EVALUATED_ORIGINAL_SHORT_CIRCUIT'
        for d in r['failure_days']:
            assert d['day'] > r['day'] and d['need'] - d['capacity'] == d['deficit'] > 0
            assert d['base_need'] <= d['base_capacity'] and d['need'] - d['base_need'] == d['added_work'] == d['quote_calendar_work']
    results = {}
    for phase, part in groups.items():
        results[phase] = {'all': analyze(part),
             'by_project_type': {kind: analyze([r for r in part if (r['item'] in ANIMALS) == (kind == 'animal')]) for kind in ('crop', 'animal')},
             'by_item': {item: analyze([r for r in part if r['item'] == item]) for item in sorted({r['item'] for r in part})}}
    crops = [r for r in groups['initial_offer'] if r['item'] not in ANIMALS]
    animals = [r for r in groups['initial_offer'] if r['item'] in ANIMALS]
    animal_median = statistics.median(r['failure_days'][0]['deficit'] for r in animals)
    examples = [
        ('初报价作物最小首日差额；同值选最早step/报价序号', min(crops, key=lambda r: (r['failure_days'][0]['deficit'], r['step'], r['quote_ordinal_in_step']))),
        ('初报价动物最接近该类首日差额中位数；同值选最早step/报价序号', min(animals, key=lambda r: (abs(r['failure_days'][0]['deficit'] - animal_median), r['step'], r['quote_ordinal_in_step']))),
        ('复查中首失败偏移最远；同值选最早step/报价序号', min(groups['admission_recheck'], key=lambda r: (-r['first_failure_offset'], r['step'], r['quote_ordinal_in_step'])))]
    result = {'schema': 'r9-future-only-labor-diagnostic-v2', 'status': 'READONLY_COMPLETE',
              'candidate_calls': 0, 'engine_steps': 0, 'new_independent_matches': 0,
              'source_probe_candidate_calls': 719, 'source_probe_saved_engine_steps': 719,
              'population': '只取原捕获failure_class=future_only；初报价和准入复查单独分母，不合并分位数',
              'quantiles': 'p10/25/75/90/95采用ceil(p*N) nearest-rank；median使用中间值均值',
              'groups': results, 'examples': [{'selection': rule, 'record': record} for rule, record in examples],
              'claims': {'funding_feasibility': 'NOT_EVALUATED', 'new_route_feasibility': 'NOT_ESTABLISHED',
                         'independent_projects': False, 'eligible_promotion_evidence': False}}
    for p, expected in inputs.items():
        assert sha(p) == expected, ('SOURCE_CHANGED_DURING_ANALYSIS', p)
    dump(HERE / 'analysis.json', result)
    lines = ['# 仅未来劳动拒绝：缺口大小与项目类型', '',
        '本分析只读已经完成的 R9 首场探针，候选调用 0、引擎 0、新比赛 0。只取当前日可行、未来某日不可行的记录。初次报价和准入复查分开计量；同一项目可能跨帧重复、在不同阶段重复，以下是报价尝试分布。', '',
        '| 报价阶段 | 尝试数 | 首失败差额 min / median / p90 / max | 首失败偏移 min / median / p90 / max | 基线已不可行 |',
        '|---|---:|---|---|---:|']
    names = {'initial_offer': '初次报价', 'admission_recheck': '准入复查'}
    for phase, part in results.items():
        a = part['all']; d = a['first_failure_deficit']; t = a['first_failure_offset']
        lines.append(f'| {names[phase]} | {a["attempts"]:,} | {d["min"]} / {d["median"]} / {d["p90"]} / {d["max"]} | {t["min"]} / {t["median"]} / {t["p90"]} / {t["max"]} 天 | {a["baseline_infeasible_attempts"]} |')
    lines += ['', '全部仅未来拒绝中，原基线在整个预测窗口内可行；当前 trial 也可行。原调度允许新增项目引起未来雇工增加，不能把原基线容量等同 trial 容量。本样本所有首失败 trial 容量均为 298；首缺口满足“原基线需求 + 本项目日历工作量 − 新 trial 容量”。因此每条差额是该原 trial 在该未来日需要释放的模型容量，不是可直接统一扣减的路线折扣。只修首失败日也不保证通过：同一次报价可能在多个未来日失败。', '',
        '| 阶段 | 项目 | 尝试数 | 首日差额 median / p90 / max | 首日偏移 median / max |',
        '|---|---|---:|---|---|']
    for phase, part in results.items():
        for item, a in part['by_item'].items():
            d = a['first_failure_deficit']; t = a['first_failure_offset']
            lines.append(f'| {names[phase]} | {item} | {a["attempts"]:,} | {d["median"]} / {d["p90"]} / {d["max"]} | {t["median"]} / {t["max"]} 天 |')
    lines += ['', '| 代表性原记录（选择规则见 JSON） | step / day / hour | 商品 / 位置 | 首失败日 | 基线需要 / 容量 | trial需要 / 容量 | 所有失败日 |',
        '|---|---|---|---:|---|---|---|']
    for i, (_, r) in enumerate(examples, 1):
        d = r['failure_days'][0]
        lines.append(f'| {i}：{names[r["phase"]]} | {r["step"]} / {r["day"]} / {r["hour"]} | {r["item"]} / {r["position"]} | {d["day"]} | {d["base_need"]} / {d["base_capacity"]} | {d["need"]} / {d["capacity"]} | '+', '.join(str(x['day']) + '(差' + str(x['deficit']) + ')' for x in r['failure_days'])+' |')
    lines += ['', '对于“保持当前日 R9、只重做未来整日服务表示”的下一方案，最低证据覆盖应包括未来照护、采收和回仓服务的日级合并，并对每个未来日重新核容量，保留第一天及之后的所有缺口；不能只给当天路线规划加分，也不能固定减一个经验比例。现金约束继续独立按原顺序评估。', '',
        '本诊断没有执行未来路线，不能证明共享服务可实现多少节省，也不能证明被劳动拒绝的项目财务可行。模型净值和首产日只是冻结 R9 原报价；任何盈利或晋级判断仍须独立候选与预注册测试。', '',
        '`analysis.json` 保存初报价/复查各自的完整差额直方图、偏移直方图、首失败日、基线/trial容量、余量、项目增量、失败日数量以及商品/作物动物细分；三个例子保留完整原记录。源 `labor_rejections.jsonl.gz` 不变。']
    (HERE / 'REPORT.md').write_text('\n'.join(lines) + '\n')
    dump(HERE / 'delivery_manifest.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'candidate_calls': 0,
         'engine_steps': 0, 'new_independent_matches': 0, 'inputs': inputs,
         'files': {**{str(HERE / n): sha(HERE / n) for n in ('analysis.json', 'REPORT.md')}, str(Path(__file__).resolve()): sha(Path(__file__))}})
    print(json.dumps({'groups': {k: {'attempts': v['all']['attempts'],
                      'deficit': {x: v['all']['first_failure_deficit'][x] for x in ('min', 'median', 'p90', 'max')},
                      'offset': {x: v['all']['first_failure_offset'][x] for x in ('min', 'median', 'p90', 'max')}} for k, v in results.items()},
                      'delivery_sha256': sha(HERE / 'delivery_manifest.json')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
