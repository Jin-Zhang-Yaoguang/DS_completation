"""已保存真实动作的服务路径与日级劳动拒绝诊断；不运行候选或引擎。"""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;MODEL=ROOT.parent.parent
gpath=MODEL/'evaluation/r9_pass_diagnostic_s0/games.jsonl';g=json.loads(gpath.read_text().splitlines()[0]);assert g['status']=='DONE'
seat=g['candidate_seat'];rs=g['strategy_diagnostics'][seat][str(seat)]['investment_receipts'];tracepath=Path(g['trace']['path'])
assert hashlib.sha256(tracepath.read_bytes()).hexdigest()==g['trace']['sha256']
trace=json.load(gzip.open(tracepath,'rt'))['actions']
units=[[a[seat]['farmer']]+a[seat]['hands'] for a in trace]
MOVES={'EAST','WEST','NORTH','SOUTH'}
daily=[]
for d in range(30):
    ids=range(d*24,min(719,(d+1)*24));counts=Counter(a[0]for s in ids for a in units[s]);overlap=[]
    for s in ids:
        passes=sum(a[0]=='PASS'for a in units[s])
        if passes and rs[s]['rejected_types'].get('labor',0):overlap.append({'step':s,'pass':passes,'labor_rejected_quotes':rs[s]['rejected_types']['labor'],
           'accepted_plan_remaining_today_work':rs[s]['work'].get(str(d),0),'accepted_plan_remaining_today_capacity':rs[s]['capacity'][str(d)]})
    start=rs[d*24]
    daily.append({'day':d,'requested_action_counts':dict(counts),'actual_trace_unit_slots':sum(counts.values()),
                  'opening_model_work':start['work'].get(str(d),0),'opening_model_capacity':start['capacity'][str(d)],
                  'labor_rejected_quote_evaluations':sum(rs[s]['rejected_types'].get('labor',0)for s in ids),
                  'pass_and_labor_rejection_frames':overlap})
epath=ROOT/'opened_trace_audit/r9_pass_s0_mechanism/events.jsonl.gz';events=[json.loads(x)for x in gzip.open(epath,'rt')]
water=defaultdict(list)
for e in events:
    if e['seat']==seat and e['kind']=='water':water[(e['day'],e['unit'])].append(e)
homes=[(4,4),(5,4),(4,5),(5,5)]
def distance(p,q):return abs(p[0]-q[0])+abs(p[1]-q[1])
def warehouse(p):return min(homes,key=lambda q:(distance(p,q),q))
chains=[]
def save_chain(chain):
    if len(chain)<3:return
    first,last=chain[0]['decision_step'],chain[-1]['decision_step'];u=chain[0]['unit'];ps=[e['position']for e in chain]
    if len({tuple(p)for p in ps})!=len(ps):return
    moves=sum(units[s][u][0]in MOVES for s in range(first+1,last+1))
    passes=sum(units[s][u][0]=='PASS'for s in range(first+1,last+1))
    access=sum(max(1,distance(p,warehouse(p)))for p in ps)
    enter=distance(ps[0],warehouse(ps[0]));exit_dist=distance(ps[-1],warehouse(ps[-1]))
    chains.append({'day':chain[0]['day'],'unit':u,'first_step':first,'last_step':last,'positions':ps,'successful_water_count':len(ps),
                   'recorded_between_moves':moves,'recorded_between_pass':passes,'model_separate_access_distance':access,
                   'one_route_from_nearest_warehouse_moves':enter+moves,'one_route_return_to_warehouse_moves':enter+moves+exit_dist,
                   'separate_access_minus_closed_route':access-(enter+moves+exit_dist),
                   'labor_rejection_in_same_window':sum(rs[s]['rejected_types'].get('labor',0)for s in range(first,last+1))})
for (d,u),ee in water.items():
    chain=[]
    for e in ee:
        if chain:
            lo,hi=chain[-1]['decision_step'],e['decision_step']
            intervening=[units[s][u][0]if u<len(units[s])else'MISSING' for s in range(lo+1,hi)]
            if any(op not in MOVES|{'PASS'}for op in intervening):save_chain(chain);chain=[]
        chain.append(e)
    save_chain(chain)
chains.sort(key=lambda c:(-c['separate_access_minus_closed_route'],-c['successful_water_count'],c['first_step']))
out={'source_game_sha256':hashlib.sha256(gpath.read_bytes()).hexdigest(),'events_sha256':hashlib.sha256(epath.read_bytes()).hexdigest(),
     'candidate_calls':0,'engine_replays':0,'trace_pass_requests':sum(x['requested_action_counts'].get('PASS',0)for x in daily),
     'same_frame_pass_and_labor_rejection_count':sum(len(x['pass_and_labor_rejection_frames'])for x in daily),'days':daily,'water_chains':chains,
     'scope':['PASS为官方已执行动作trace中的指令，不把所有PASS当作可拼接劳动。',
              'opening_model_work是开盘剩余计划，包含许可/预测；当天实际动作包含后来新增任务，二者不是严格同一集合。',
              'water_chains从真实成功浇水事件取连续同工人服务，无期间其它作业；首段仓→首格和尾段返仓为明确对照假设，不是假称该工人实际从仓开始。',
              '闭合路径仅证明相同已服务格集合可以共享路径；未证明某个被拒报价有足够连续空闲或会增加现金。']}
p=HERE/'service_calendar_probe.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'path':str(p),'pass':out['trace_pass_requests'],'overlap_frames':out['same_frame_pass_and_labor_rejection_count'],'best_chain':chains[0]if chains else None},ensure_ascii=False))
