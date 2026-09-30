#!/usr/bin/env python3
"""只读汇总已完成探针；不调用候选或引擎。"""
import collections, gzip, hashlib, json
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'captured_r9_opened_s0'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dump(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')

def main():
    if (HERE / 'report_summary.json').exists():
        raise RuntimeError('REFUSE_REPORT_OVERWRITE')
    inputs = {str(p): sha(p) for p in SOURCE.iterdir() if p.is_file()}
    validation = json.loads((SOURCE / 'validation.json').read_text())
    for p, expected in validation['files'].items():
        assert sha(Path(p)) == expected, ('SOURCE_CHANGED', p)
    summary = json.loads((SOURCE / 'summary.json').read_text())
    assert summary['status'] == 'DIAGNOSTIC_COMPLETE'
    rows = [json.loads(line) for line in gzip.open(SOURCE / 'labor_rejections.jsonl.gz', 'rt')]
    steps = [json.loads(line) for line in gzip.open(SOURCE / 'step_context.jsonl.gz', 'rt')]
    assert len(steps) == 719 and len(rows) == summary['labor_rejections']
    classes = ('current_only', 'future_only', 'current_and_future')
    table = []
    for label in classes:
        select = [r for r in rows if r['failure_class'] == label]
        table.append({'group': label, 'attempts': len(select), 'share_of_labor_attempts': len(select) / len(rows),
                      'distinct_steps': len({r['step'] for r in select}),
                      'baseline_infeasible_attempts': sum(r['baseline_already_infeasible'] for r in select),
                      'modeled_net_positive_attempts': sum(r['quote']['net_cash_model'] > 0 for r in select)})
    modes = {label: dict(collections.Counter(r['phase'] for r in rows if r['failure_class'] == label)) for label in classes}
    first_by_class = {label: next((r for r in rows if r['failure_class'] == label), None) for label in classes}
    baseline_first = next((r for r in rows if r['baseline_already_infeasible']), None)
    max_offset = max(rows, key=lambda r: r['first_failure_offset'])
    max_deficit = max(rows, key=lambda r: max(d['deficit'] for d in r['failure_days']))
    near = collections.Counter()
    for r in rows:
        n = r['first_failure_offset']
        near['today' if n == 0 else 'tomorrow' if n == 1 else '2_to_7_days' if n <= 7 else '8_or_more_days'] += 1
    hourly = []
    for hour in range(24):
        select = [r for r in rows if r['hour'] == hour]
        hourly.append({'hour': hour, 'attempts': len(select), 'groups': dict(collections.Counter(r['failure_class'] for r in select)),
                       'baseline_infeasible': sum(r['baseline_already_infeasible'] for r in select)})
    result = {'status': 'DIAGNOSTIC_COMPLETE', 'calls': {'candidate': 719, 'saved_action_engine_steps': 719,
               'opponent_candidate': 0, 'new_independent_matches': 0}, 'source_cash': summary['cash'],
              'rejections': summary['rejection_totals'], 'labor_classes': table, 'labor_by_quote_phase': modes,
              'first_failure_horizon': dict(near), 'first_failure_offset': summary['first_failure_day_offset'],
              'labor_distinct_decision_steps': len({r['step'] for r in rows}),
              'baseline_already_infeasible_attempts': sum(r['baseline_already_infeasible'] for r in rows),
              'first_by_class': first_by_class, 'first_baseline_infeasible': baseline_first,
              'furthest_first_failure_example': max_offset, 'largest_deficit_example': max_deficit,
              'labor_by_item': summary['by_item'], 'labor_by_hour': hourly,
              'raw_evidence_directory': str(SOURCE), 'qualification': summary['qualification'],
              'source_validation': {'action_matches': summary['action_comparisons'], 'receipt_matches': summary['per_frame_receipts_compared'],
                 'snapshot_matches': summary['saved_snapshots_compared'], 'diagnostics_equal': summary['diagnostics_equal_source'],
                 'terminal_equal': summary['terminal_equal_source'], 'source_shas_unchanged': summary['all_source_shas_unchanged']}}
    for p, expected in inputs.items():
        assert sha(Path(p)) == expected, ('INPUT_CHANGED_DURING_REPORT', p)
    dump(HERE / 'report_summary.json', result)
    labels = {'current_only': '仅当天失败', 'future_only': '仅未来失败', 'current_and_future': '当天与未来均失败'}
    lines = ['# R9 首场内部劳动报价诊断', '',
             '本次完整恢复了真实内部状态，719 次候选调用与 719 次保存官方动作逐帧对应；没有新独立比赛。全部动作、719 条完整 receipt、31 个保存状态摘要、终态和完整 diagnostics 均与原局一致，源 SHA 未变。监控开销不用于 G0 或性能结论。', '',
             f'原局现金为 {summary["cash"][0]:,.0f} 对 PASS {summary["cash"][1]:,.0f}。本次直接捕获拒绝：劳动 {summary["rejection_totals"]["labor"]:,}、资金前缀 {summary["rejection_totals"]["cash_prefix"]:,}、启动或成熟时限 {summary["rejection_totals"]["startup_or_maturity"]:,}、模型净值非正 {summary["rejection_totals"]["nonpositive_net"]:,}，与原 receipt 按帧闭合。', '',
             '| 原劳动失败范围 | 报价尝试 | 占劳动拒绝 | 涉及决策帧 | 基线已有缺口 | 模型净值为正 |',
             '|---|---:|---:|---:|---:|---:|']
    for r in table:
        lines.append(f'| {labels[r["group"]]} | {r["attempts"]:,} | {r["share_of_labor_attempts"]:.2%} | {r["distinct_steps"]} | {r["baseline_infeasible_attempts"]:,} | {r["modeled_net_positive_attempts"]:,} |')
    lines += ['', '计数是报价尝试，初次报价与准入复查、同站点跨帧重复均保留。各类涉及帧可能重叠，不能相加为独立帧，更不能解释为损失项目数或可买动物数。', '',
              '劳动分支在模型净值与现金前缀检查之前短路返回。表中净值为正只表示原代码已计算的模型数值为正，所有劳动拒绝的现金可行性仍是未评估；不能据此声称收入机会被错误拒绝。', '',
              f'共有 {result["labor_distinct_decision_steps"]} 个决策帧出现劳动拒绝；{result["baseline_already_infeasible_attempts"]:,} 次报价发生时，报价前的原承诺基线已不可行。首失败日分层：{dict(near)}。最远的首失败日距决策日 {max_offset["first_failure_offset"]} 天。', '',
              '| 第一条原报价实例 | 决策 step / day / hour | 商品 / 位置 | 首失败日 | 原需求 / 容量 | 基线需求 / 容量 |',
              '|---|---|---|---:|---:|---:|']
    for label, r in first_by_class.items():
        if r:
            d = r['failure_days'][0]
            lines.append(f'| {labels[label]} | {r["step"]} / {r["day"]} / {r["hour"]} | {r["item"]} / {r["position"]} | {d["day"]} | {d["need"]} / {d["capacity"]} | {d["base_need"]} / {d["base_capacity"]} |')
    lines += ['', '直接证据是冻结 R9 原函数的 `next_work` 和原返回 `capacity_by_day`。没有重跑调度、删除原义务或构造反事实。真实路径服务是否能共享、模型是否重复计交通，需要下一候选在明确表示下验证；本表只能定位原约束发生在哪些日子。', '',
              '数据位置：`captured_r9_opened_s0/labor_rejections.jsonl.gz` 保存全部劳动拒绝的需要/容量/报价增量；`step_context.jsonl.gz` 保存每帧实际动作、所选专家、准入报价、前后合同摘要；`summary.json` 和本目录 `report_summary.json` 提供紧凑统计。', '',
              '原记录没有 719 帧全量观测文件，因此只声称同源引擎/种子/保存动作重建，加上述保存摘要和内部输出的完整复核，不声称每帧全观测与原文件逐字段比较。', '',
              '冻结与复现：`probe_freeze.json` 在第一次候选调用前锁定脚本/协议及全部来源。`capture_budget.py` 为本次探针固定版本；本报告脚本只读已完成捕获，候选调用和引擎步数均为 0。']
    (HERE / 'REPORT.md').write_text('\n'.join(lines) + '\n')
    dump(HERE / 'report_validation.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(),
          'inputs': inputs, 'script_sha256': sha(Path(__file__)), 'candidate_calls': 0, 'engine_steps': 0,
          'outputs': {str(HERE / name): sha(HERE / name) for name in ('REPORT.md', 'report_summary.json')}})
    print(json.dumps({'rejections': result['rejections'], 'classes': table, 'horizon': dict(near),
                      'furthest_first_failure_offset': max_offset['first_failure_offset']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
