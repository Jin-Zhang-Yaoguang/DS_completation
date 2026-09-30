"""只读已完成收据、真实事件和源累计账，不调用候选或引擎。"""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,json,hashlib
HERE=Path(__file__).resolve().parent
MODEL=next(p for p in HERE.parents if p.name=='v125_closed_loop_economy')
run=MODEL/'evaluation/r8_pass_diagnostic_s0';game=json.loads((run/'games.jsonl').read_text().splitlines()[0]);seat=game['candidate_seat']
r=game['strategy_diagnostics'][seat][str(seat)]['investment_receipts'];assert len(r)==719
ad=HERE.parent/'opened_trace_audit/r8_pass_s0_mechanism';v=json.loads((ad/'validation.json').read_text());eventsfile=ad/'events.jsonl.gz'
assert hashlib.sha256(eventsfile.read_bytes()).hexdigest()==v['files']['events.jsonl.gz']
events=[json.loads(s)for s in gzip.open(eventsfile,'rt')];events=[e for e in events if e['seat']==seat]
byday=defaultdict(Counter);quantities=defaultdict(Counter)
for e in events:
 if e['kind']=='market':byday[e['day']][e['op']+'|'+e['item']]+=e['quantity']*e['price'];quantities[e['day']][e['op']+'|'+e['item']]+=e['quantity']
hire_cumulative={}
for pair in game['daily']:
 s=pair[seat];hire_cumulative[s['day']]=sum(s['audit_cumulative']['market'].get('HIRE_cash',{}).values())
previous=0;table=[]
for day in range(30):
 current=hire_cumulative[day];hire_cash=current-previous;previous=current
 x=r[day*24];ex=x['existing'];feedtoday=ex['feed'].get(str(day),0);allfeed=sum(ex['feed'].values())
 rows=r[day*24:min((day+1)*24,719)]
 table.append({'day':day,'opening_cash':x['actual_cash'],'opening_wheat':x['actual_wheat'],'today_feed_units_model':feedtoday,'future_feed_units_model':allfeed-feedtoday,
               'current_feed_cash_lower_bound':max(0,feedtoday-x['actual_wheat']), 'current_feed_cash_lower_bound_units':'WHEAT units; zero means existing physical stock covers modeled current feed count, not route proof',
               'full_horizon_feed_cash_reserved':ex['feed_cash'],'full_horizon_hire_cash_reserved':ex['hire_cash'],'total_reserved':ex['reserved_cash'],
               'shortfall':max(0,ex['reserved_cash']-x['actual_cash']),'available':x['remaining_cash'],'actual_day_feed_purchase_cash':byday[day]['BUY_PRODUCT|WHEAT'],
               'actual_day_hire_cash':hire_cash,'actual_day_nonwheat_sales':sum(c for key,c in byday[day].items()if key.startswith('SELL|')and key!='SELL|WHEAT'),
               'actual_seed_animal_cash':sum(c for key,c in byday[day].items()if key.startswith(('BUY_SEED|','BUY_ANIMAL|'))),
               'cash_rejection_frames':sum(bool(z['rejected_types'].get('cash'))for z in rows),'cash_rejection_quote_evaluations':sum(z['rejected_types'].get('cash',0)for z in rows),
               'existing_shortfall_frames':sum(z['existing']['reserved_cash']>z['actual_cash']for z in rows)})
rej=Counter();frames=Counter()
for x in r:rej.update(x['rejected_types']);frames.update({k:1 for k,n in x['rejected_types'].items()if n})
first=next(e for e in events if e['kind']=='market'and e['op']=='SELL'and e['item']!='WHEAT')
report={'source_game_sha256':hashlib.sha256((run/'games.jsonl').read_bytes()).hexdigest(),'source_events_sha256':v['files']['events.jsonl.gz'],'candidate_calls':0,'engine_replays':0,
        'table':table,'rejected_quote_evaluations':dict(rej),'frames_by_rejection_type':dict(frames),'total_existing_shortfall_frames':sum(t['existing_shortfall_frames']for t in table),
        'first_nonwheat_sale':first,'first_sale_elapsed':first['decision_step']+1,'first_ten_days_nonwheat_sales':sum(t['actual_day_nonwheat_sales']for t in table[:10]),
        'first_ten_days_feed_cash':sum(t['actual_day_feed_purchase_cash']for t in table[:10]),'first_ten_days_hire_cash':sum(t['actual_day_hire_cash']for t in table[:10]),
        'source_scope':'no initial/externally purchased nonwheat stock in source; official first-sale qualification remains parent statistician responsibility'}
(HERE/'cash_constraint.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:report[k]for k in report if k!='table'},ensure_ascii=False,indent=2))
for t in table[:11]:print(t)
