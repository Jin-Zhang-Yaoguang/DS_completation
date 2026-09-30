#!/usr/bin/env python3
"""只读R8完成后的投资收据/原动作与可选官方重放事件；不导入候选或重放引擎。"""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import argparse,csv,gzip,hashlib,json,math

EXPECTED='b7080c1181fb672ecc4f0bf96ad580cef5a0f80ed5d39d32908610c02423e693'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def close(a,b):return abs(a-b)<=1e-7*max(1,abs(a),abs(b))
def loadrun(path):
    run=path.resolve();m=json.loads((run/'run_manifest.json').read_text());g=json.loads((run/'games.jsonl').read_text().splitlines()[0]);assert g['status']=='DONE'and g['calls']==719
    s=g['candidate_seat'];rr=g['strategy_diagnostics'][s][str(s)]['investment_receipts'];assert [r['step']for r in rr]==list(range(719))
    tp=Path(g['trace']['path']);assert sha(tp)==g['trace']['sha256'];tr=json.load(gzip.open(tp));assert len(tr['actions'])==719
    return m,g,rr,tr

def main():
    p=argparse.ArgumentParser();p.add_argument('--r8-run',type=Path,required=True);p.add_argument('--r7-run',type=Path,required=True)
    p.add_argument('--r7-step-audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--events',type=Path)
    p.add_argument('--completion-confirmed',action='store_true');a=p.parse_args()
    if not a.completion_confirmed:raise SystemExit('根尚未确认DONE：不读取结果')
    if a.output.exists()and any(a.output.iterdir()):raise RuntimeError('拒绝覆盖已有分析')
    a.output.mkdir(parents=True,exist_ok=True)
    m8,g8,r8,t8=loadrun(a.r8_run);m7,g7,r7,t7=loadrun(a.r7_run);assert m8['candidate']['entry_sha256']==EXPECTED
    assert g8['seed']==g7['seed']and g8['candidate_seat']==g7['candidate_seat'];seat=g8['candidate_seat']
    rows7=[json.loads(x)for x in gzip.open(a.r7_step_audit,'rt')];assert len(rows7)==719
    violations=[];rows=[];mode=Counter();active=Counter();defaults=Counter();initial_scores=[]
    for r,actionpair in zip(r8,t8['actions']):
        step=r['step'];acts=actionpair[seat];scores=r['expert_selection_scores'];selected=r['selected_expert_score'];expert=r['expert'];mode[r['selection_objective']]+=1
        if r['selection_objective']!='terminal_net':violations.append({'step':step,'kind':'unexpected_selection_mode'})
        finite_scores={k:v for k,v in scores.items()if v is not None}
        if finite_scores:
            active[expert]+=1
            if selected is None or not close(selected,max(finite_scores.values()))or not close(selected,finite_scores[expert]):violations.append({'step':step,'kind':'expert_not_initial_maximum'})
        else:
            defaults[expert]+=1
            if selected is not None:violations.append({'step':step,'kind':'nonempty_selection_without_quotes'})
        if r['market_intents']!=acts['market']:violations.append({'step':step,'kind':'receipt_trace_market_mismatch'})
        for q in r['admitted']:
            if not close(q['selection_score'],q['net_cash_model']):violations.append({'step':step,'kind':'selection_not_net','project':q})
            if q['score']<=0:violations.append({'step':step,'kind':'nonpositive_execution_score','project':q})
            else:
                implied_work=q['net_cash_model']/q['score']
                if implied_work<1 or not close(implied_work,round(implied_work)):violations.append({'step':step,'kind':'execution_ratio_implied_labor_not_positive_integer','project':q})
        expected=r['remaining_cash']+sum(q['cash_reserved_model']for q in r['admitted'])+r['land_cash']
        if not close(expected,max(0,r['actual_cash']-r['existing']['reserved_cash'])):violations.append({'step':step,'kind':'budget_identity'})
        req=Counter();unit=Counter();admitted=Counter(q['item']for q in r['admitted'])
        for order in acts['market']:
            req[(order[0],order[1]if len(order)>1 else'')]+=order[2]if len(order)>2 else 1
        for act in[acts['farmer']]+acts.get('hands',[]):
            if act[0]in('PLANT','PLACE','PICKUP'):unit[(act[0],act[1])]+=act[2]if len(act)>2 else 1
            elif act[0].startswith('BUILD_'):unit[(act[0],'')]+=1
        # 初始专家分与逐项重新报价不是同一个时点，后者可能因顺序冲击变化。
        rows.append({'step':step,'day':step//24,'hour':step%24,'expert':expert,'active_expert':bool(finite_scores),
                     'initial_scores':scores,'selected_initial_score':selected,'cash':r['actual_cash'],'wheat':r['actual_wheat'],
                     'existing_reserved':r['existing']['reserved_cash'],'remaining_cash':r['remaining_cash'],'new_reserved':sum(q['cash_reserved_model']for q in r['admitted']),
                     'admitted_items':dict(admitted),'admitted_quotes':r['admitted'],'in_transit':r['existing']['in_transit'],
                     'rejected_types':r['rejected_types'],'market_requests':{'|'.join(k):v for k,v in req.items()},'unit_requests':{'|'.join(k):v for k,v in unit.items()},
                     'land_cash':r['land_cash']})
    events=[]
    if a.events:
        events=[json.loads(line)for line in gzip.open(a.events,'rt')if line.strip()];events=[e for e in events if e['seat']==seat]
    actual=defaultdict(Counter);actualcash=defaultdict(Counter);placements=[];plants=[];losses=[]
    for e in events:
        st=e['decision_step']
        if e['kind']=='market':actual[st][e['op']+'|'+e['item']]+=e['quantity'];actualcash[st][e['op']+'|'+e['item']]+=e['quantity']*e['price']
        elif e['kind']=='place_animal':placements.append(e)
        elif e['kind']=='plant':plants.append(e)
        elif e['kind'].startswith('eod_')or e['kind']=='overflow':losses.append(e)
    # 可选事件必须与源整局真实市场数量闭合，才能写成真实成交时序。
    if a.events:
        total=sum(actual.values(),Counter())
        for op in['BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','SELL']:
            expected=g8['action_audit']['actual_market_ledger'][seat].get(op+'_qty',{})
            got={key.split('|',1)[1]:v for key,v in total.items()if key.startswith(op+'|')}
            assert got==expected,(op,got,expected)
    snapshots={}
    for pair in g8['daily']:
        snap=pair[seat];snapshots[snap['day']]=snap
    days=[]
    for day in range(30):
        rr=[r for r in rows if r['day']==day];old=[r for r in rows7 if r['day']==day];pr=sum((Counter(r['market_requests'])for r in rr),Counter());ut=sum((Counter(r['unit_requests'])for r in rr),Counter());ap=sum((Counter(r['admitted_items'])for r in rr),Counter());re=sum((Counter(r['rejected_types'])for r in rr),Counter())
        snap=snapshots.get(day,{})
        ac=sum((actual[r['step']]for r in rr),Counter());acash=sum((actualcash[r['step']]for r in rr),Counter())
        days.append({'day':day,'decisions':len(rr),'r8_open_cash':rr[0]['cash'],'r7_open_cash':old[0]['cash'],'r8_last_cash':rr[-1]['cash'],'r7_last_cash':old[-1]['cash'],
                     'r8_new_quote_items':dict(ap),'r7_new_quote_count':sum(r['new_permit_quotes']for r in old),'r8_active_experts':dict(Counter(r['expert']for r in rr if r['active_expert'])),
                     'r8_no_quote_default_frames':sum(not r['active_expert']for r in rr),'r8_rejected_types':dict(re),'r7_rejected_types':dict(sum((Counter(r['rejected_types'])for r in old),Counter())),
                     'r8_market_requests':dict(pr),'r8_unit_requests':dict(ut),'r8_actual_market':dict(ac)if a.events else None,'r8_actual_market_cash':dict(acash)if a.events else None,
                     'r8_snapshot_step':snap.get('step'),'r8_snapshot_board':snap.get('board'),'r8_snapshot_quadrants':snap.get('quadrants'),
                     'r7_last_decision_crops':old[-1]['crop_count'],'r7_last_decision_animals':old[-1]['placed_animal_count'],'r7_last_decision_lands':old[-1]['land_count']})
    first_requests={}
    for r in rows:
        for key,n in r['market_requests'].items():
            if key not in first_requests:first_requests[key]={'step':r['step'],'quantity':n,'cash':r['cash']}
    report={'source_sha256':EXPECTED,'seed':g8['seed'],'seat':seat,'candidate_reward':g8['candidate_reward'],'r7_reward':g7['candidate_reward'],
            'receipt_rows':len(rows),'violations':violations,'selection_modes':dict(mode),'active_expert_frames':dict(active),'no_quote_default_frames':dict(defaults),
            'first_requests':first_requests,'days':days,'first_step':rows[0],'placements':placements,'actual_plants':plants,
            'actual_event_evidence_attached':bool(a.events),'actual_event_sha256':sha(a.events)if a.events else None,
            'definitions':{'selection_score':'本轮默认为预算后净终值，仅用于初始专家比较、初始许可排序；非组合收益。',
                           'net_cash_model':'同一项目在许可时重新预算后的预计净终值。',
                           'score':'原net/labor执行分；日志未保存labor，审计只能核隐含劳动为正整数，不能独立核整个劳动模型。',
                           'initial_vs_sequential':'expert_selection_scores是初始可行报价，各许可项目会受前序许可的物价/资源影响重算，两个时点不得混同。',
                           'quantity_scope':'quote次数、发出请求、官方真实成交分别列；未附官方事件时不从请求推断真实成交时序。',
                           'daily_board':'source daily快照为日末最后动作前或终态，字段给出真实snapshot_step，不当成精确EOD后地块组成。',
                           'scope':'同一个已打开种子的收据解释，不是新对局或因果强度证明。'}}
    dump(a.output/'selection_analysis.json',report)
    with gzip.open(a.output/'steps.jsonl.gz','wt')as z:
        for r in rows:z.write(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n')
    dump(a.output/'manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(__file__),
         'r8_games_sha256':sha(a.r8_run/'games.jsonl'),'r7_games_sha256':sha(a.r7_run/'games.jsonl'),'r7_step_audit_sha256':sha(a.r7_step_audit),
         'source_sha256':EXPECTED,'candidate_imported':False,'agent_calls':0,'official_replays':0,'actual_events':str(a.events)if a.events else None})
    print(json.dumps({'output':str(a.output),'violations':len(violations),'active_experts':dict(active),'defaults':dict(defaults),'actual_events':bool(a.events),'first_requests':first_requests},ensure_ascii=False))

if __name__=='__main__':main()
