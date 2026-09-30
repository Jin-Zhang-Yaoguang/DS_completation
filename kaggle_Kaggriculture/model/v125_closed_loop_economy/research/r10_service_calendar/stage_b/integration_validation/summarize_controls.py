"""只读已结束控制输出，不调用策略或引擎。"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    run = HERE / 'controls_v1'
    sp = run / 'summary.json'; summary = json.loads(sp.read_bytes())
    files = {str(sp): sha(sp), str(Path(__file__).resolve()): sha(__file__)}
    compact = {'scope': '人工集成工程控制，0新完整比赛；部分报价不等于最终许可。', 'status': summary['status'],
        'counts': summary['counts'], 'source_drift': summary['source_drift'], 'legacy': [], 'executor': [], 'default': [], 'profile': []}
    for meta in summary['records']:
        p = Path(meta['path']); assert sha(p) == meta['sha256']; files[str(p)] = sha(p)
        d = json.loads(gzip.decompress(p.read_bytes()))
        base = {'id': d['id'], 'error': d.get('run_error', {}).get('message'), 'check_failures': [k for k, v in d['checks'].items() if not v]}
        if d['id'].startswith('legacy_'):
            base.update(paired_steps=len(d['rows']), all_dispatch_equal=all(r['R9_dispatched'] == r['R10_legacy_dispatched'] for r in d['rows']),
                all_official_post_observations_equal=all(r['R9_after'] == r['R10_legacy_after'] for r in d['rows']),
                call_count=len(d['call_times']), max_seconds_by_kind={kind: max(r['seconds'] for r in d['call_times'] if r['kind'] == kind) for kind in {r['kind'] for r in d['call_times']}})
            compact['legacy'].append(base)
        elif d['id'].startswith('r9_executor'):
            diag=d['diagnostic']; seat=d['fixture']['seat']
            base.update({k: v for k,v in diag.items() if k not in ('harvest_receipts','explicit_place_receipts','missing_harvest_assets','missing_explicit_place_assets')})
            base.update(missing_harvest_count=len(diag['missing_harvest_assets']), missing_explicit_place_count=len(diag['missing_explicit_place_assets']),
                final_cash=d['final']['farms'][seat]['money'], final_shed=d['final']['private']['shed'],
                hired=sum(r['actual_hired'] for r in d['hires']), hire_cash=sum(r['cash_cost'] for r in d['hires']),
                actual_atomic_action_counts=dict(Counter(e['action'][0] for e in d['unit_events'])), max_seconds=max(r['seconds'] for r in d['call_times']))
            compact['executor'].append(base)
        elif d['id'].startswith('default_agent'):
            base.update(calls=d['call_times'], official_steps=len(d['rows']), complete_plan_returned=not bool(base['error']))
            compact['default'].append(base)
        elif d['id'].startswith('pressure_'):
            base['modes']=[]
            old = { (b['item'],tuple(b['position'])):b for b in d['modes'][0]['budget_returns'] if b['phase']=='initial_offer' }
            for m in d['modes']:
                finished = [b for b in m['budget_returns'] if b['reason'] != 'EXCEPTION_OR_NON_TUPLE']
                successful = [b for b in finished if b['route_proof'] and b['route_proof']['labor_feasible_after_routes']]
                routes = [r for r in m['route_returns'] if type(r['result']) is bool]
                overlaps=[]
                for b in finished:
                    k=(b['item'],tuple(b['position']))
                    if b['phase']=='initial_offer' and k in old:
                        a=old[k]
                        overlaps.append(a['quote_scores']==b['quote_scores'] and a['labor']==b['labor'] and a['workload']==b['workload'])
                row={'mode':m['mode'],'plan_returned':'plan' in m,'seconds_profiled_not_performance_evidence':m['seconds_profiled_not_performance_evidence'],
                     'completed_budget_return_count':len(finished),'interrupted_budget_return_count':len(m['budget_returns'])-len(finished),
                     'completed_route_return_count':len(routes),'interrupted_route_return_count':len(m['route_returns'])-len(routes),
                     'completed_route_true':sum(r['result'] for r in routes),'completed_route_false':sum(not r['result'] for r in routes),
                     'all_completed_route_invariants':all(all(r['invariants'].values()) for r in routes) if routes else None,
                     'completed_budget_reason_counts':dict(Counter(str(b['reason']) for b in finished)),
                     'route_successful_completed_budgets':len(successful),'successful_route_then_actual_cash_checks':sum(b['prefix_calls'] for b in successful),
                     'successful_route_then_cash_rejected':sum(b['reason']=='cash_prefix' for b in successful),
                     'paired_initial_quote_count':len(overlaps),'all_reached_initial_cost_capacity_score_equal':all(overlaps) if overlaps else None,
                     'whole_plan_counter_closure':'PASS' if 'plan' in m and not base['error'] else 'PENDING_INTERRUPTED_PLAN',
                     'examples':[{'item':b['item'],'pos':b['position'],'reason':b['reason'],'actual_cash':b['actual_cash'],
                                  'prefix_calls':b['prefix_calls'],'funding_admission':b['funding_admission'],'scores':b['quote_scores'],
                                  'route_days':list(b['route_proof']['route_feasibility_by_day'])} for b in successful[:3]]}
                base['modes'].append(row)
            compact['profile'].append(base)
    compact['limitations']=['初态人为给定，不证明自然可达。','legacy仅比较dispatch和完整官方后观测，不保存独立applied事件。',
        'R9 day10全部48产品EOD入仓、无损失；只证明同日主动PLACE/SELL未兑现，day11未执行。',
        '本轮weedSpawnChance0.005，旧保存证书控制0；当天服务/市场发生于末EOD之前，post-EOD全态不可称同配置。',
        '预算170完整入口/170短步是上限；超时调用按真实尝试计，未返回动作不推进官方步。',
        '监控函数开销不作策略延迟；超时后的部分报价不可宣称全计划准入或现金闭合。']
    for p,v in files.items(): assert sha(p)==v
    out=HERE/'compact_summary.json'; assert not out.exists();out.write_text(json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
    files[str(out)]=sha(out)
    man=HERE/'summary_manifest.json'; assert not man.exists();man.write_text(json.dumps({'files':files,'candidate_calls':0,'engine_calls':0},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(out),'sha256':sha(out),'manifest_sha256':sha(man)},ensure_ascii=False))


if __name__=='__main__':main()
