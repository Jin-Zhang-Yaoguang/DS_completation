#!/usr/bin/env python3
"""只读已完成收据、动作及逐步真实账本；不再重放引擎。"""
from pathlib import Path
from collections import Counter
import csv,gzip,json,hashlib
HERE=Path(__file__).resolve().parent
BASE=HERE/'opened_pass_s0'
RUN=HERE.parents[3]/'evaluation'/'r7_pass_diagnostic_s0'
# 目录层级显式从父目录名称定位，避免误读相邻研究。
MODEL=next(p for p in HERE.parents if p.name=='v125_closed_loop_economy')
RUN=MODEL/'evaluation'/'r7_pass_diagnostic_s0'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(name,x):(HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
report=json.loads((BASE/'receipt_audit.json').read_text())
rows=[json.loads(x)for x in gzip.open(BASE/'step_audit.jsonl.gz','rt')]
source=json.loads((RUN/'games.jsonl').read_text().splitlines()[0]);seat=source['candidate_seat']
trace=json.load(gzip.open(source['trace']['path']));receipts=source['strategy_diagnostics'][seat][str(seat)]['investment_receipts']
assert len(rows)==len(trace['actions'])==len(receipts)==719
shortfalls=[];excess=[];requested=Counter();actual=Counter()
for row,actions in zip(rows,trace['actions']):
    req=Counter()
    for order in actions[seat]['market']:
        if order[0]in ['BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','SELL']:req[(order[0],order[1])]+=order[2]
    for(op,item),n in req.items():
        got=row['actual_ledger'].get(op+'_qty',{}).get(item,0);requested[(op,item)]+=n;actual[(op,item)]+=got
        if got<n:shortfalls.append({'step':row['step'],'op':op,'item':item,'requested':n,'actual':got,'missing':n-got})
        if got>n:excess.append({'step':row['step'],'op':op,'item':item,'requested':n,'actual':got})
post={'source_games_sha256':sha(RUN/'games.jsonl'),'source_step_audit_sha256':sha(BASE/'step_audit.jsonl.gz'),'script_sha256':sha(__file__),
      'agent_calls':0,'engine_replays':0,'request_shortfalls':shortfalls,'actual_exceeds_request':excess,
      'totals':[{'op':op,'item':item,'requested':n,'actual':actual[(op,item)]}for(op,item),n in sorted(requested.items())]}
dump('request_completion_postcheck.json',post)
rej=Counter();rejection_frames=Counter()
for r in rows:
    rej.update(r['rejected_types']);rejection_frames.update({k:1 for k,n in r['rejected_types'].items()if n})
capital_rejected=[r for r in rows if r['rejected_types'].get('cash')]
no_cash_after_day10=all(not r['rejected_types'].get('cash')for r in rows if r['day']>10)
last_of_days={d:next(r for r in reversed(rows)if r['day']==d)for d in range(30)}
extra={'request_postcheck_shortfalls':len(shortfalls),'rejection_quote_evaluations':dict(rej),'frames_with_rejection_type':dict(rejection_frames),
       'cash_rejection_steps':[r['step']for r in capital_rejected],'cash_rejection_day_range':[min(r['day']for r in capital_rejected),max(r['day']for r in capital_rejected)]if capital_rejected else None,
       'no_cash_rejections_after_day10':no_cash_after_day10,
       'step0':rows[0],'first_positive_plant':next(r['step']for r in rows if r['actual_plant']),
       'first_sales':next({'step':r['step'],'day':r['day'],'sales_cash':r['actual_sale_cash'],'ledger':r['actual_ledger']}for r in rows if r['actual_sale_cash']),
       'first_lands':[{'step':r['step'],'lands_before':r['land_count'],'cash':r['cash'],'paid':r['actual_new_investment_cash']}for r in rows if r['actual_buy_land']],
       'animal_purchases':[{'step':r['step'],'cash':r['cash'],'ledger':r['actual_ledger']}for r in rows if r['actual_new_animals']],
       'baseline_capacity_observations':len(report['baseline_overcapacity_days']),
       'unique_baseline_capacity_steps':len({r['step']for r in report['baseline_overcapacity_days']}),
       'baseline_capacity_days':sorted({r['step']//24 for r in report['baseline_overcapacity_days']}),
       'daily_summary':[{'day':d,'cash':last_of_days[d]['cash'],'crops':last_of_days[d]['crop_count'],'placed_animals':last_of_days[d]['placed_animal_count'],'lands':last_of_days[d]['land_count']}for d in range(30)],
       'total_real_seed_animal_land_cash':sum(r['actual_new_investment_cash']for r in rows),
       'total_real_hire_cash':sum(sum(r['actual_ledger'].get('HIRE_cash',{}).values())for r in rows),
       'total_real_feed_cash':sum(sum(r['actual_ledger'].get('BUY_PRODUCT_cash',{}).values())for r in rows)}
dump('findings.json',extra)
print(json.dumps({k:v for k,v in extra.items()if k not in('step0','daily_summary','cash_rejection_steps')},ensure_ascii=False,indent=2))
