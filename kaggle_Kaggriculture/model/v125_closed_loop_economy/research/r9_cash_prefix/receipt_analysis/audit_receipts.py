"""只读完整R9收据、已存动作与官方事件；不导入候选，不重放引擎。"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse, gzip, hashlib, json, math

EXPECTED='e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0'
PRODUCTIVE={'WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','COW','SHEEP','GOOSE'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(a,b):return abs(a-b)<=1e-7*max(1.,abs(a),abs(b))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def readrun(p):
    summary=json.loads((p/'summary.json').read_text())
    assert summary['status']=='COMPLETE' and summary['done_games']==summary['expected_games']==1
    game=json.loads((p/'games.jsonl').read_text().splitlines()[0]);assert game['status']=='DONE' and game['calls']==719
    seat=game['candidate_seat'];rows=game['strategy_diagnostics'][seat][str(seat)]['investment_receipts']
    assert [x['step']for x in rows]==list(range(719))
    trace=Path(game['trace']['path']);assert sha(trace)==game['trace']['sha256']
    actions=json.load(gzip.open(trace,'rt'))['actions'];assert len(actions)==719
    manifest=json.loads((p/'run_manifest.json').read_text())
    return game,rows,actions,manifest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--parent-run',type=Path,required=True)
    ap.add_argument('--events',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    assert not a.output.exists(),'禁止覆盖已有证据'
    g,rs,actions,manifest=readrun(a.run);old,oldrows,oldactions,_=readrun(a.parent_run);seat=g['candidate_seat']
    assert manifest['candidate']['entry_sha256']==EXPECTED and g['seed']==old['seed'] and seat==old['candidate_seat']
    val=json.loads((a.events.parent/'validation.json').read_text());assert sha(a.events)==val['files'][a.events.name]
    events=[json.loads(x)for x in gzip.open(a.events,'rt')];events=[e for e in events if e['seat']==seat]
    violations=[];checked=Counter();rows=[];reasons=Counter();statuses=Counter()
    def test(ok,kind,step,extra=None):
        checked[kind]+=1
        if not ok:violations.append({'step':step,'kind':kind,'detail':extra})
    def book_check(book,day,cash,step,name):
        balance=float(cash);first=None;computed=[];credits=Counter()
        for batch in book['credit_batches']:
            d=batch['credit_day'];credits[str(d)]+=batch['cash_model']
            test(day<d<=29 and batch['product'] not in ('WHEAT','FERTILIZER') and batch['quantity']>0,'eligible_batch_dates_products',step,name)
        test(len({(x['credit_day'],x['product'])for x in book['credit_batches']})==len(book['credit_batches']),'one_batch_per_day_product',step,name)
        for d in range(day,30):
            k=str(d);expense=book['expenses_by_day'][k]
            test(close(expense,book['feed_cash_by_day'][k]+book['hire_cash_by_day'][k]+(book['fixed_cash_today'] if d==day else 0)),'expense_components',step,[name,d])
            balance-=expense;computed.append(balance)
            test(close(balance,book['before_credit'][k]),'before_credit_algebra',step,[name,d])
            if balance < -1e-9 and first is None:first=d
            credit=book['credits_by_day'].get(k,0)
            test(close(credit,credits[k]),'batch_daily_cash_closure',step,[name,d])
            if d==day:test(credit==0,'current_day_credit_zero',step,name)
            balance+=credit if d>day else 0
            test(close(balance,book['after_credit'][k]),'after_credit_algebra',step,[name,d])
        minimum=min(computed)
        test(close(minimum,book['minimum']) and book['first_negative_day']==first and book['feasible']==(first is None),'prefix_summary',step,name)
        test(close(max(0,minimum),book['additional_current_spend']),'additional_spend_is_minimum',step,name)
        test(close(sum(book['expenses_by_day'].values()),book['full_horizon_cash_outflow']),'full_cost_sum',step,name)
        test(book['feed_cash_by_day'][str(day)]+1e-8>=book['current_market_feed']['cash_limit'],'current_feed_cash_margin_covered',step,name)
    market_by_step=defaultdict(Counter);cash_by_step=defaultdict(Counter);plants=[];placements=[]
    for e in events:
        if e['kind']=='market':
            market_by_step[e['decision_step']][e['op']+'|'+e['item']]+=e['quantity']
            cash_by_step[e['decision_step']][e['op']+'|'+e['item']]+=e['quantity']*e['price']
        elif e['kind']=='plant':plants.append(e)
        elif e['kind']=='place_animal':placements.append(e)
    total_market=sum(market_by_step.values(),Counter())
    for op in ('BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','SELL'):
        got={k.split('|',1)[1]:v for k,v in total_market.items()if k.startswith(op+'|')}
        test(got==g['action_audit']['actual_market_ledger'][seat].get(op+'_qty',{}),'official_events_source_qty_closure',-1,op)
    first_difference=None
    for step,r in enumerate(rs):
        day=step//24;initial,final=r['initial_funding_book'],r['funding_book'];act=actions[step][seat]
        book_check(initial,day,r['actual_cash'],step,'initial');book_check(final,day,r['actual_cash'],step,'final')
        test(r['cash_funding_model']=='cash_prefix' and r['selection_objective']=='terminal_net','funding_selection_modes',step)
        test(close(final['additional_current_spend'],r['remaining_cash']),'reported_remaining_spend',step)
        test(r['market_intents']==act['market'] and len(act['market'])<=10,'trace_market_intents_slots',step)
        initbatch={(x['credit_day'],x['product']):x for x in initial['credit_batches']};endbatch={(x['credit_day'],x['product']):x for x in final['credit_batches']}
        test(initbatch.keys()==endbatch.keys() and all(v['quantity']==endbatch[k]['quantity'] and endbatch[k]['cash_model']<=v['cash_model']+1e-8 for k,v in initbatch.items()),'source_quantity_frozen_and_credit_nonincreasing',step)
        test(bool(r['credit_source_positions']) or not final['credit_batches'],'no_credit_without_source_positions',step)
        fixed_new=sum(q['cash_reserved_model']-q['feed_cash_model']-q['hire_cash_model'] for q in r['admitted'])
        test(close(final['fixed_cash_today'],initial['fixed_cash_today']+fixed_new+r['land_cash']),'fixed_commitment_sum',step)
        test(len(r['funding_admissions'])==len(r['admitted']),'funding_admission_length',step)
        for q,z in zip(r['admitted'],r['funding_admissions']):
            statuses[z['status']]+=1
            test(q['item']==z['item'] and q['position']==z['position'] and close(q['cash_reserved_model'],z['original_full_horizon_new_cash']),'admission_identity_old_cost',step)
            test(close(q['net_cash_model'],q['selection_score']) and q['score']>0,'three_score_semantics_partial',step)
            if z['status']=='EXISTING_SHORTFALL_ZERO_NEW_CASH_REUSE':test(q['cash_reserved_model']==0,'reuse_old_new_cash_zero',step)
            else:test(z['status']=='PREFIX_FEASIBLE' and z['trial_minimum']>=-1e-8,'normal_admission_nonnegative_minimum',step)
        if not final['feasible'] and r['admitted']:
            test(not initial['feasible'] and all(z['status']=='EXISTING_SHORTFALL_ZERO_NEW_CASH_REUSE' for z in r['funding_admissions'])
                 and all(final['before_credit'][k]+1e-7>=v for k,v in initial['before_credit'].items())
                 and all(final['after_credit'][k]+1e-7>=v for k,v in initial['after_credit'].items()),'aggregate_shortfall_reuse_not_worse',step)
        if first_difference is None and act!=oldactions[step][seat]:first_difference=step
        moneys=cash_by_step[step];sales=sum(v for k,v in moneys.items()if k.startswith('SELL|'));buys=sum(v for k,v in moneys.items()if k.startswith('BUY_'))
        nextcash=rs[step+1]['actual_cash'] if step<718 else g['candidate_reward']
        other_cost=r['actual_cash']+sales-buys-nextcash
        test(other_cost>=-1e-7,'cash_bridge_nonnegative_fixed_residual',step)
        test(buys+other_cost<=r['actual_cash']+1e-7,'actual_spend_no_same_frame_sale_borrow',step)
        reasons.update(r['rejected_types'])
        rows.append({'step':step,'day':day,'cash':r['actual_cash'],'wheat':r['actual_wheat'],'expert':r['expert'],
                     'source_positions':r['credit_source_positions'],'initial_credit':sum(initial['credits_by_day'].values()),
                     'initial_full_outflow':initial['full_horizon_cash_outflow'],'initial_minimum':initial['minimum'],'initial_first_negative_day':initial['first_negative_day'],
                     'final_minimum':final['minimum'],'final_first_negative_day':final['first_negative_day'],'current_additional_spend':r['remaining_cash'],
                     'initial_current_expense':initial['expenses_by_day'][str(day)],'initial_future_expense':initial['full_horizon_cash_outflow']-initial['expenses_by_day'][str(day)],
                     'admitted':r['admitted'],'admission_statuses':r['funding_admissions'],'rejected_types':r['rejected_types'],'market_intents':act['market'],
                     'actual_market_qty':dict(market_by_step[step]),'actual_market_cash':dict(moneys),'actual_other_fixed_cost':other_cost,
                     'parent_cash':oldrows[step]['actual_cash'],'parent_old_remaining':oldrows[step]['remaining_cash']})
    snapshots={}
    for pair in g['daily']:
        snap=pair[seat];step=snap['step'];snapshots[snap['day']]=snap
        if step<719:
            expected=sorted([t[:2] for t in snap['tiles']if t[2]in PRODUCTIVE]);observed=sorted(rs[step]['credit_source_positions'])
            test(expected==observed,'source_positions_vs_saved_real_snapshot',step)
            test(close(snap['money'],rs[step]['actual_cash']),'cash_vs_saved_real_snapshot',step)
    days=[]
    for day in range(30):
        rr=rows[day*24:min(719,(day+1)*24)];actual=sum((Counter(x['actual_market_cash'])for x in rr),Counter());snap=snapshots[day]
        days.append({'day':day,'opening':rr[0],'snapshot_step':snap['step'],'snapshot_board':snap['board'],'snapshot_quadrants':snap['quadrants'],
                     'quote_counts':dict(Counter(q['item']for x in rr for q in x['admitted'])),
                     'rejection_counts':dict(sum((Counter(x['rejected_types'])for x in rr),Counter())),
                     'initial_negative_frames':sum(x['initial_minimum'] < -1e-8 for x in rr),
                     'first_negative_calendar_days':dict(Counter(str(x['initial_first_negative_day']) for x in rr if x['initial_first_negative_day']is not None)),
                     'actual_market_cash':dict(actual),'actual_hire_land_cash_combined':sum(x['actual_other_fixed_cost']for x in rr),
                     'actual_plantings':sum(e['day']==day for e in plants),'actual_placements':sum(e['day']==day for e in placements)})
    first_sale=next(e for e in events if e['kind']=='market' and e['op']=='SELL' and e['item']!='WHEAT')
    result={'source_sha256':EXPECTED,'seed':g['seed'],'seat':seat,'reward':g['candidate_reward'],'parent_reward':old['candidate_reward'],
            'receipt_count':len(rs),'checked':dict(checked),'violations':violations,'funding_statuses':dict(statuses),'rejections':dict(reasons),
            'first_action_difference':first_difference,'first_action_difference_row':rows[first_difference] if first_difference is not None else None,
            'days':days,'actual_placements':placements,'actual_first_nonwheat_sale':first_sale,
            'actual_first_ten_days_nonwheat_sale_cash':sum(v for d in days[:10]for k,v in d['actual_market_cash'].items()if k.startswith('SELL|')and k!='SELL|WHEAT'),
            'pending':['每帧资产身份与完整成熟日历：仅30个已存真实状态可对位置做独立检查，其它帧未重新执行引擎。',
                       '每项trial完整前缀未记：能核汇总及trial_minimum，不能恢复每项中间所有日期的前缀。',
                       '供给完整库存、义务requirements未全记：不能仅靠收据独立核全组重价和全部物理负债。',
                       '一般未来信用兑现归因需固定预测版本和出生资产来源，不能将719帧信用相加；本报告先保留后续专门归因。'],
            'candidate_imported':False,'candidate_calls':0,'engine_replays':0}
    a.output.mkdir(parents=True)
    dump(a.output/'receipt_audit.json',result)
    with gzip.open(a.output/'steps.jsonl.gz','wt')as z:
        for row in rows:z.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    dump(a.output/'manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':EXPECTED,'script_sha256':sha(__file__),
         'games_sha256':sha(a.run/'games.jsonl'),'parent_games_sha256':sha(a.parent_run/'games.jsonl'),'events_sha256':sha(a.events),
         'candidate_imported':False,'candidate_calls':0,'engine_replays':0})
    print(json.dumps({'output':str(a.output),'violations':len(violations),'checks':sum(checked.values()),'first_difference':first_difference,
                     'statuses':dict(statuses),'reward':g['candidate_reward'],'early_nonwheat_cash':result['actual_first_ten_days_nonwheat_sale_cash']},ensure_ascii=False))

if __name__=='__main__':main()
