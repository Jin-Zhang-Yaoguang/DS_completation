#!/usr/bin/env python3
"""冻结R7收据一致性审计；只重放已完成的原动作，不导入或调用候选。"""
from __future__ import annotations
import argparse, copy, csv, gzip, hashlib, importlib.util, json, math, statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_SOURCE='ea57c77215d6728e64a3c46c5cf1c2b21f2efa72d12dbb53240b544e27500e7f'
COST={'WHEAT':10,'CARROT':20,'TOMATO':50,'STRAWBERRY':100,'MELON':80,'COW':400,'SHEEP':500,'GOOSE':300}
ANIMALS={'COW','SHEEP','GOOSE'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def plain(x):return json.loads(json.dumps(x))
def finite(x):
    if isinstance(x,(int,float)):return math.isfinite(x)
    if isinstance(x,dict):return all(finite(v)for v in x.values())
    if isinstance(x,list):return all(finite(v)for v in x)
    return True

def goods(private,item):return private['shed'].get(item,0)+sum(i.get(item,0)for i in private['inventories'])
def delta_ledger(after,before):
    return {op:{item:n-before.get(op,{}).get(item,0)for item,n in items.items()if n-before.get(op,{}).get(item,0)}for op,items in after.items()}
def amount(ledger,kind):return sum(ledger.get(kind,{}).values())
def mean(xs):return statistics.mean(xs)if xs else None

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--game-index',type=int,default=0)
    p.add_argument('--completion-confirmed',action='store_true',help='根已确认唯一完整运行结束，才可读取结果')
    args=p.parse_args()
    if not args.completion_confirmed:raise SystemExit('拒绝读取：须先获根确认完整运行结束，再显式传--completion-confirmed。')
    run=args.run_dir.resolve();out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise RuntimeError('输出目录非空，拒绝覆盖证据')
    source=json.loads((run/'games.jsonl').read_text().splitlines()[args.game_index]);manifest=json.loads((run/'run_manifest.json').read_text())
    assert source['status']=='DONE' and source['calls']==719 and source['statuses']==['DONE','DONE']
    assert manifest['candidate']['entry_sha256']==EXPECTED_SOURCE
    seat=source['candidate_seat'];diagnostic=source['strategy_diagnostics'][seat][str(seat)]
    receipts=diagnostic['investment_receipts'];steps=[r['step']for r in receipts]
    assert steps==list(range(719)) and len(set(steps))==719,('incomplete_receipt_steps',steps)
    assert all(finite(r)for r in receipts)
    tracepath=Path(source['trace']['path']);assert sha(tracepath)==source['trace']['sha256']
    trace=json.load(gzip.open(tracepath));assert len(trace['actions'])==719 and trace['seed']==source['seed']
    for key in ['candidate','opponent','engine']:
        for path,digest in manifest[key]['files'].items():assert sha(path)==digest,('file_drift',path)
    harness=Path(manifest['harness']['path']);assert sha(harness)==manifest['harness']['sha256']
    spec=importlib.util.spec_from_file_location('r7_receipt_replay_harness',harness);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    make,rules,fast,engine=h.import_engines();assert engine['composite_sha256']==manifest['engine']['composite_sha256']
    e=h.Engine('official',source['seed'],make,fast)
    out.mkdir(parents=True,exist_ok=True)
    dump(out/'audit_manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':EXPECTED_SOURCE,
         'script_sha256':sha(__file__),'games_sha256':sha(run/'games.jsonl'),'manifest_sha256':sha(run/'run_manifest.json'),
         'trace_sha256':sha(tracepath),'seed':source['seed'],'seat':seat,'workers':1,'candidate_imported':False,'agent_calls':0,
         'saved_actions_replayed':719,'source_game_reused':True,'new_match_run':False,'new_replay_opened':False})
    rows=[];violations=[];limits=[];base_deficits=[];baseline_capacity=[];new_deficit_zero_cash=[]
    def flag(step,kind,**details):violations.append({'step':step,'kind':kind,**details})
    instrument=h.Instrument(rules)
    with instrument:
        for idx,(receipt,actions)in enumerate(zip(receipts,trace['actions'])):
            obs=e.observe(seat);farm=obs['farms'][seat];private=obs['private'];action=actions[seat]
            assert obs['step']==idx
            if receipt['actual_cash']!=farm['money']:flag(idx,'actual_cash_mismatch',recorded=receipt['actual_cash'],actual=farm['money'])
            if receipt['actual_wheat']!=goods(private,'WHEAT'):flag(idx,'actual_wheat_mismatch',recorded=receipt['actual_wheat'],actual=goods(private,'WHEAT'))
            if receipt.get('market_intents')!=action.get('market',[]):flag(idx,'market_intents_mismatch')
            expected_units=[{'unit':u,'action':a}for u,a in enumerate([action.get('farmer',['PASS'])]+action.get('hands',[]))if a and(a[0]in('PLANT','PLACE')or a[0].startswith('BUILD_'))]
            if receipt.get('unit_investment_intents')!=expected_units:flag(idx,'unit_intents_mismatch')
            if len(action.get('market',[]))>10:flag(idx,'market_slots_exceeded',orders=action['market'])
            ex=receipt['existing'];admitted=receipt['admitted']
            base_reserved=ex['reserved_cash'];new_cash=sum(q['cash_reserved_model']for q in admitted)
            available=max(0.,farm['money']-base_reserved)
            residual=receipt['remaining_cash']+new_cash+receipt['land_cash']-available
            if abs(residual)>1e-6:flag(idx,'shared_cash_identity_residual',residual=residual)
            components=ex['feed_cash']+ex['hire_cash']+ex['committed_fixed_cash']
            if abs(base_reserved-components)>1e-6:flag(idx,'existing_cash_components_mismatch')
            shortage=max(0.,base_reserved-farm['money'])
            if shortage:
                base_deficits.append({'step':idx,'cash':farm['money'],'existing_reserved':base_reserved,'shortage':shortage})
                if admitted and new_cash==0:new_deficit_zero_cash.append({'step':idx,'count':len(admitted),'items':dict(Counter(q['item']for q in admitted))})
                if new_cash>1e-6:flag(idx,'positive_new_cash_despite_base_shortfall',shortage=shortage,new_cash=new_cash)
            if not 0<=ex['owned_feed_used']<=receipt['actual_wheat']:flag(idx,'existing_owned_wheat_credit_exceeds_stock')
            if new_cash<0 or receipt['remaining_cash']<0:flag(idx,'negative_budget')
            positions=[tuple(q['position'])for q in admitted]
            if len(positions)!=len(set(positions)):flag(idx,'duplicate_admitted_position')
            expected_buy=Counter();build_only=0;fixed_cash=0
            for q in admitted:
                item=q['item'];fixed=q['cash_reserved_model']-q['feed_cash_model']-q['hire_cash_model']
                fixed_cash+=fixed
                if min(q['cash_reserved_model'],q['feed_cash_model'],q['hire_cash_model'],q['feed_cost_model'])<-1e-6:flag(idx,'negative_project_component',project=q)
                if abs(fixed)>1e-6 and abs(fixed-COST[item])>1e-6:flag(idx,'project_fixed_cash_mismatch',item=item,fixed=fixed)
                if q['build_first']:
                    build_only+=1
                elif fixed>1e-6:
                    expected_buy[('BUY_ANIMAL'if item in ANIMALS else'BUY_SEED',item)]+=1
                x,y=q['position']
                if farm['tiles'][y][x]=='LOCKED':flag(idx,'new_project_on_locked_land',position=[x,y])
                if item in ANIMALS and not q['build_first']:
                    tile=farm['tiles'][y][x]
                    if not isinstance(tile,dict)or'animal'in tile or tile.get('kind')!=('COOP'if item=='GOOSE'else'PASTURE'):
                        flag(idx,'animal_purchase_without_ready_structure',position=[x,y],tile=tile)
            request=Counter()
            for order in action.get('market',[]):
                if len(order)>2:
                    if type(order[2])is not int or not 1<=order[2]<=100:flag(idx,'market_quantity_outside_contract',order=order)
                    request[(order[0],order[1])]+=order[2]
            for key,n in request.items():
                if key[0]in('BUY_ANIMAL','BUY_SEED')and n>expected_buy[key]:flag(idx,'unlicensed_new_purchase_request',order=list(key),requested=n,licensed=expected_buy[key])
            for key,n in expected_buy.items():
                if request[key]!=n:limits.append({'step':idx,'kind':'licensed_purchase_not_requested','order':list(key),'licensed':n,'requested':request[key]})
            slack=[];day_violations=[]
            for d,n in receipt['work'].items():
                cap=receipt['capacity'].get(d,receipt['capacity'].get(str(d),0));slack.append(cap-n)
                if n>cap:
                    added=n-ex['work'].get(str(d),ex['work'].get(d,0));event={'step':idx,'work_day':int(d),'work':n,'capacity':cap,'new_work':added}
                    if added>0 and admitted:flag(idx,'new_work_exceeds_capacity',**{k:v for k,v in event.items()if k!='step'})
                    else:baseline_capacity.append(event)
                    day_violations.append(event)
            before_ledger=plain(dict(instrument.ledger[seat]));before_counts=dict(instrument.counts[seat])
            instrument.before(e,actions,idx);e.step(copy.deepcopy(actions))
            after=e.observe(seat);ledger=delta_ledger(plain(dict(instrument.ledger[seat])),before_ledger)
            actual_buy=Counter({(op[:-4],item):n for op,items in ledger.items()if op.endswith('_qty')for item,n in items.items()})
            for key,n in actual_buy.items():
                if key[0]in('BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','SELL')and n>request[key]:flag(idx,'actual_quantity_exceeds_request',order=list(key),actual=n,requested=request[key])
            actual_purchases={op:ledger.get(op+'_qty',{})for op in ['BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','HIRE','BUY_LAND']}
            actual_purchase_cash=sum(amount(ledger,op+'_cash')for op in ['BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','HIRE','BUY_LAND'])
            actual_sale_cash=amount(ledger,'SELL_cash')
            cash_delta=after['farms'][seat]['money']-farm['money']
            if abs(cash_delta-(actual_sale_cash-actual_purchase_cash))>1e-6:flag(idx,'actual_cash_bridge_residual',cash_delta=cash_delta,sales=actual_sale_cash,purchases=actual_purchase_cash)
            actual_new_cost=amount(ledger,'BUY_ANIMAL_cash')+amount(ledger,'BUY_SEED_cash')+amount(ledger,'BUY_LAND_cash')
            if actual_new_cost>fixed_cash+receipt['land_cash']+1e-6:flag(idx,'actual_new_fixed_spend_exceeds_license',actual=actual_new_cost,licensed=fixed_cash+receipt['land_cash'])
            def changed(op):return instrument.counts[seat].get('changed_'+op,0)-before_counts.get('changed_'+op,0)
            n_hire=amount(ledger,'HIRE_qty');hire_requested=sum(o[0]=='HIRE'for o in action.get('market',[]))
            if n_hire!=hire_requested:limits.append({'step':idx,'kind':'hire_request_not_fully_committed','requested':hire_requested,'actual':n_hire})
            board=Counter()
            for line in farm['tiles']:
                for t in line:
                    if isinstance(t,dict):board[t.get('animal',t.get('crop',t.get('kind','unknown')))]+=1
            row={'step':idx,'day':obs['day'],'hour':obs['hour'],'expert':receipt['expert'],'cash':farm['money'],'actual_wheat':receipt['actual_wheat'],
                 'existing_reserved_cash':base_reserved,'existing_cash_shortfall':shortage,'existing_feed_cash':ex['feed_cash'],'existing_hire_cash':ex['hire_cash'],
                 'existing_owned_wheat_used':ex['owned_feed_used'],'new_permit_quotes':len(admitted),'build_only_quotes':build_only,
                 'new_cash_reserved':new_cash,'new_feed_cash_reserved':sum(q['feed_cash_model']for q in admitted),'new_hire_cash_reserved':sum(q['hire_cash_model']for q in admitted),
                 'new_feed_opportunity':sum(q['feed_cost_model']for q in admitted),'new_fixed_cash_reserved':fixed_cash,'land_reserved_cash':receipt['land_cash'],
                 'remaining_cash':receipt['remaining_cash'],'shared_cash_residual':residual,'minimum_daily_labor_slack':min(slack)if slack else None,
                 'overcapacity_days':len(day_violations),'current_hands':len(farm['hands']),'land_count':len(farm['unlocked_quadrants']),
                 'crop_count':sum(board[c]for c in COST if c not in ANIMALS),'placed_animal_count':sum(board[c]for c in ANIMALS),
                 'in_transit_animals':sum(ex['in_transit'].values()),'contract_count':ex['contract_count'],
                 'actual_new_investment_cash':actual_new_cost,'actual_purchase_cash':actual_purchase_cash,'actual_sale_cash':actual_sale_cash,
                 'actual_hires':n_hire,'actual_new_animals':amount(ledger,'BUY_ANIMAL_qty'),'actual_new_seeds':amount(ledger,'BUY_SEED_qty'),
                 'actual_buy_land':amount(ledger,'BUY_LAND_qty'),'actual_plant':changed('PLANT'),'actual_build':changed('BUILD_PASTURE')+changed('BUILD_COOP'),
                 'market_slots':len(action.get('market',[])),'actual_purchases':actual_purchases,'actual_ledger':ledger,
                 'rejected_types':receipt['rejected_types'],'admitted_items':dict(Counter(q['item']for q in admitted))}
            rows.append(row)
    assert e.done()and e.rewards()==source['rewards']
    assert h.snapshot([e.observe(s)for s in range(2)])==source['terminal']
    for op in ['BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','SELL','HIRE','BUY_LAND']:
        assert dict(instrument.ledger[seat].get(op+'_qty',{}))==source['action_audit']['actual_market_ledger'][seat].get(op+'_qty',{}),op
    days=[]
    for day in range(30):
        rr=[r for r in rows if r['day']==day];a=rr[0];z=rr[-1]
        rec={'day':day,'decisions':len(rr),'opening_cash':a['cash'],'last_decision_cash':z['cash'],'max_existing_shortfall':max(r['existing_cash_shortfall']for r in rr),
             'shortfall_frames':sum(r['existing_cash_shortfall']>0 for r in rr),'mean_existing_reserved':mean([r['existing_reserved_cash']for r in rr]),
             'permit_quote_count':sum(r['new_permit_quotes']for r in rr),'build_only_quote_count':sum(r['build_only_quotes']for r in rr),
             'frames_without_new_cash_license':sum(r['new_cash_reserved']==0 for r in rr),'mean_new_cash_reserved':mean([r['new_cash_reserved']for r in rr]),
             'mean_remaining_cash':mean([r['remaining_cash']for r in rr]),'actual_investment_cash':sum(r['actual_new_investment_cash']for r in rr),
             'actual_animals_bought':sum(r['actual_new_animals']for r in rr),'actual_seeds_bought':sum(r['actual_new_seeds']for r in rr),
             'actual_plants':sum(r['actual_plant']for r in rr),'actual_builds':sum(r['actual_build']for r in rr),'actual_land_bought':sum(r['actual_buy_land']for r in rr),
             'last_decision_crops':z['crop_count'],'last_decision_placed_animals':z['placed_animal_count'],'last_decision_in_transit':z['in_transit_animals'],
             'last_decision_lands':z['land_count'],'max_hands':max(r['current_hands']for r in rr),'market_full_frames':sum(r['market_slots']==10 for r in rr),
             'rejected_types':dict(sum((Counter(r['rejected_types'])for r in rr),Counter())),'experts':dict(Counter(r['expert']for r in rr))}
        days.append(rec)
    # 阈值在读局前锁定：前日有实际种子/动物/土地投入，次日实际投入下降至少50%。
    contractions=[{'day':d['day'],'previous_day_cash':days[i-1]['actual_investment_cash'],'current_day_cash':d['actual_investment_cash'],
                   'decline_fraction':1-d['actual_investment_cash']/days[i-1]['actual_investment_cash'],
                   'shortfall_frames':d['shortfall_frames'],'opening_cash':d['opening_cash'],'rejected_types':d['rejected_types']}
                  for i,d in enumerate(days)if i and days[i-1]['actual_investment_cash']>0 and d['actual_investment_cash']<=.5*days[i-1]['actual_investment_cash']]
    # 另一项连续窗口：已有正现金许可后，连续24决策没有正现金新增许可；不把quote次数当独立投资数。
    drought=[]
    for i in range(1,len(rows)-23):
        if rows[i-1]['new_cash_reserved']>0 and all(r['new_cash_reserved']==0 for r in rows[i:i+24]):
            drought.append({'start_step':i,'end_step':i+23,'day':i//24,'cash_start':rows[i]['cash'],'existing_shortfall_frames':sum(r['existing_cash_shortfall']>0 for r in rows[i:i+24])})
    report={'source_game_key':source['key'],'seed':source['seed'],'seat':seat,'candidate_reward':source['candidate_reward'],
            'receipt_complete_unique_steps_0_to_718':True,'receipt_finite':True,'terminal_and_actual_ledger_match':True,
            'violations':violations,'violation_count':len(violations),'unfulfilled_license_or_hire':limits,
            'existing_shortfall_frames':len(base_deficits),'existing_shortfall_examples':base_deficits[:30],
            'zero_new_cash_reuse_under_existing_shortfall':new_deficit_zero_cash,
            'baseline_overcapacity_days':baseline_capacity,'days':days,'first_daily_investment_contraction':contractions[0]if contractions else None,
            'all_daily_investment_contractions':contractions,'first_full_day_without_positive_new_cash_license':drought[0]if drought else None,
            'definitions':{'permit_quotes':'每帧许可报价次数；同一未执行位置可能重复，绝非实际成交项目数。','actual_investment_cash':'官方真实BUY_ANIMAL+BUY_SEED+BUY_LAND支出；HIRE与供料另列。',
                           'existing_shortfall':'存量全期预留账超过当前现金；不是已经发生的拖欠账款，也不是整段照护已经融资。','contraction':'只读局前固定阈值：实际投资现金较前一日下降至少50%，前日须>0。常规建设等待也可能触发，不能据此单独认定资金原因。',
                           'owned_wheat_scope':'收据可准确核实际总麦与存量owned_feed_used≤实际量；新增项目只记录饲料现金/机会成本，没有记录其自有麦逐日数量，故无法从收据独立闭合全体预约麦物量。',
                           'labor_scope':'核模型逐日work≤capacity及实际HIRE/市场槽；日级聚合容量不是路线与截止都可兑现的证明。',
                           'actual_event_scope':'通过冻结官方引擎重放同719动作核真实成交，无候选导入/agent调用；不构成新比赛或资格证据。'},
            'evidence_role':'ONE_OPENED_DIAGNOSTIC_NOT_PROMOTION_OR_CAUSAL_PROOF'}
    dump(out/'receipt_audit.json',report)
    with gzip.open(out/'step_audit.jsonl.gz','wt',encoding='utf-8')as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    with(out/'daily_investment.csv').open('w',newline='')as f:
        fields=[k for k in days[0]if k not in('rejected_types','experts')];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k]for k in fields}for r in days)
    dump(out/'validation.json',{'agent_calls':0,'saved_actions':719,'complete_unique_receipts':True,'actual_cash_and_wheat_checked_each_step':True,
                              'terminal_and_actual_market_ledger_matches':True,'receipt_invariant_violation_count':len(violations),'output_files':{p.name:sha(p)for p in out.iterdir()if p.is_file()}})
    print(json.dumps({'output':str(out),'violations':len(violations),'existing_shortfall_frames':len(base_deficits),'first_contraction':report['first_daily_investment_contraction']},ensure_ascii=False))

if __name__=='__main__':main()
