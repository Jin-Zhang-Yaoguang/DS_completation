#!/usr/bin/env python3
"""采购审计v2：诊断与源JSON同口径序列化后全字段比较；冻结v1保留。"""
from __future__ import annotations
import argparse,ast,collections,copy,gzip,hashlib,importlib.util,inspect,json,os,sys,time
from pathlib import Path
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
MODEL=HERE.parents[1]
OPS={'BUY_ANIMAL','BUY_SEED','BUY_LAND'}
ANIMALS={'COW','SHEEP','GOOSE'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plain(x):return json.loads(json.dumps(x))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def assets(obs,seat):
    f,p=obs['farms'][seat],obs['private'];counts=collections.Counter()
    for row in f['tiles']:
        for t in row:
            if isinstance(t,dict):
                label=t.get('crop') or t.get('animal')
                if label:counts[label]+=1
    for item in ANIMALS:
        counts[item]+=p['shed'].get(item,0)+sum(i.get(item,0) for i in p['inventories'])
    return {'assets':dict(counts),'seeds':dict(p['seeds']),'land':len(f['unlocked_quadrants']),'hands':len(f['hands']),'money':f['money'],'day':obs['day'],'hour':obs['hour'],'step':obs['step']}

class CandidateObserver:
    def __init__(self,path):
        self.path=str(path.resolve());tree=ast.parse(path.read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
        confirm=functions.get('confirm_orders');market=functions.get('market_orders')
        if confirm is None or market is None:raise RuntimeError('UNSUPPORTED_CANDIDATE_ARCHITECTURE')
        lines=[n.lineno for n in ast.walk(confirm) if isinstance(n,ast.AugAssign) and 'purchase_requested' in ast.unparse(n.target)]
        if len(lines)!=1:raise RuntimeError('CONFIRM_CAPTURE_POINT_UNCLEAR')
        self.confirm_line=lines[0];self.land_guard=None
        for node in ast.walk(market):
            if not isinstance(node,ast.If):continue
            calls=[n for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='fixed_order' and n.args and isinstance(n.args[0],ast.List)
                   and n.args[0].elts and isinstance(n.args[0].elts[0],ast.Constant) and n.args[0].elts[0].value=='BUY_LAND']
            if calls:
                ceilings=[n.comparators[0].value for n in ast.walk(node.test) if isinstance(n,ast.Compare) and isinstance(n.left,ast.Name) and n.left.id=='lands' and len(n.ops)==1
                          and isinstance(n.ops[0],ast.Lt) and isinstance(n.comparators[0],ast.Constant) and isinstance(n.comparators[0].value,int)]
                if len(ceilings)==1:self.land_guard={'ceiling':ceilings[0],'condition':ast.unparse(node.test),'line':node.lineno}
        self.calls=[];self.checks=[];self.plans=[];self.proposals=[];self.pending={};self.step=0
    def tracer(self,frame,event,arg):
        if frame.f_code.co_filename!=self.path:return None
        name=frame.f_code.co_name
        if name not in ('confirm_orders','economic_plan','market_orders','fixed_order'):return None
        loc=frame.f_locals
        if event=='call' and name=='confirm_orders':
            st=loc['st'];obs=loc['obs'];self.calls.append({'observation_step':obs['step'],'previous_last_step':st.get('last_step'),
                'previous':plain(st.get('previous')),'issued':plain(st.get('issued',[])),'unit_actions':plain(st.get('unit_actions',[])),
                'metrics_before':plain(st.get('metrics',{}))})
        elif event=='line' and name=='confirm_orders' and frame.f_lineno==self.confirm_line:
            st=loc['st'];order=loc['order'];idx=next((i for i,z in enumerate(st['issued']) if z is order),None)
            self.checks.append({'issued_step':st['last_step'],'observed_step':loc['obs']['step'],'order_index':idx,'order':plain(order),
                                'requested_in_original_code':loc['requested'],'got_in_original_code':loc['got'],
                                'raw_plant_requests_added_back':plain(loc.get('plant_used',{})),'previous':plain(loc['prev']),'now':plain(loc['now']),
                                'source_line':frame.f_lineno,'capture':'原confirm_orders执行到purchase_requested增量前，got已由原代码计算并截断'})
        elif event=='return' and name=='confirm_orders' and self.calls:
            self.calls[-1]['metrics_after']=plain(loc['st'].get('metrics',{}))
        elif event=='return' and name=='economic_plan':self.plans.append({'step':self.step,'plan':plain(arg)})
        elif event=='call' and name=='fixed_order':
            parent=frame.f_back
            if parent is None or parent.f_code.co_name!='market_orders':return self.tracer
            p=parent.f_locals;order=plain(loc['order']);op=order[0];item=order[1] if len(order)>1 else 'land';record={
                'step':self.step,'order':order,'source_line':parent.f_lineno,'orders_before':len(loc.get('orders',[])),
                'cash_before':loc.get('cash'),'cost_budgeted':loc.get('cost'),'target':None,'actual_before':None,'target_scope':'PENDING'}
            if op=='BUY_ANIMAL' and item in p.get('plan',{}).get('animals',{}):
                record.update(target=p['plan']['animals'][item],actual_before=p['own'].get(item,0),target_scope='原economic_plan返回的动物总资产目标（田间+仓库+随身）')
            elif op=='BUY_SEED' and p.get('choice')==item and 'target' in p and 'available_seeds' in p:
                record.update(target=p['target'],actual_before=p['available_seeds'],target_scope='原market_orders当前种子库存缓冲目标；不是整个作物生命周期总量',
                              seed_target_inputs={k:plain(p[k]) for k in ('choice','available_seeds','n','day','hour') if k in p})
            elif op=='BUY_LAND' and self.land_guard:
                record.update(target=self.land_guard['ceiling'],actual_before=p.get('lands'),target_scope='源码实际触发BUY_LAND的静态总土地上限；没有伪造独立计划目标变量',
                              land_guard=self.land_guard,land_trigger_inputs={k:plain(p[k]) for k in ('lands','occupied','day','cash') if k in p})
            if record['target'] is not None and record['actual_before'] is not None:record['net_target_gap']=max(0,record['target']-record['actual_before'])
            self.pending[id(frame)]=record
        elif event=='return' and name=='fixed_order' and id(frame) in self.pending:
            record=self.pending.pop(id(frame));record['accepted_by_original_budget_check']=bool(arg);self.proposals.append(record)
        return self.tracer

class OfficialObserver:
    def __init__(self,rules,engine):self.r=rules;self.e=engine;self.orig={};self.step=0;self.commits=[];self.plants=[];self.escapes=[];self.animal_overflow=[]
    def __enter__(self):
        self.interpreter=self.e.g.interpreter
        def bound(state,env,logs=None):
            self.farms={id(f):i for i,f in enumerate(state[0].observation.farms)};self.privates={id(s.observation.private):i for i,s in enumerate(state)}
            return self.interpreter(state,env)
        self.e.g.interpreter=bound
        for name,fn in [('_commit_unit',self.commit),('_do_buy_land',self.land),('_apply_unit_action',self.unit),('_daily_refresh_animals',self.animal_day),('_drop_inventories_to_shed',self.drop)]:
            self.orig[name]=getattr(self.r,name);setattr(self.r,name,fn)
        return self
    def __exit__(self,*_):
        self.e.g.interpreter=self.interpreter
        for name,fn in self.orig.items():setattr(self.r,name,fn)
    def commit(self,op,item,price,farm,private,market,*args,**kw):
        caller=inspect.currentframe().f_back;index=caller.f_locals.get('i') if caller.f_code.co_name=='_process_market' else None
        seat=self.farms[id(farm)];money=farm['money'];before=private['seeds'].get(item,0) if op=='BUY_SEED' else private['shed'].get(item,0)
        ok=self.orig['_commit_unit'](op,item,price,farm,private,market,*args,**kw)
        after=private['seeds'].get(item,0) if op=='BUY_SEED' else private['shed'].get(item,0)
        self.commits.append({'step':self.step,'seat':seat,'order_index':index,'op':op,'item':item,'success':bool(ok),'quantity':int(bool(ok)),
                             'price':price,'money_delta':farm['money']-money,'holding_before':before,'holding_after':after})
        return ok
    def land(self,farm,*args,**kw):
        caller=inspect.currentframe().f_back;index=caller.f_locals.get('i') if caller.f_code.co_name=='_process_market' else None
        old=len(farm['unlocked_quadrants']);money=farm['money'];ret=self.orig['_do_buy_land'](farm,*args,**kw);n=len(farm['unlocked_quadrants'])-old
        self.commits.append({'step':self.step,'seat':self.farms[id(farm)],'order_index':index,'op':'BUY_LAND','item':'land','success':bool(n),'quantity':n,'money_delta':farm['money']-money,'holding_before':old,'holding_after':old+n})
        return ret
    def unit(self,farm,private,idx,action,*args,**kw):
        before=dict(private['seeds']);pos=self.r._farmer_position(farm,idx);ret=self.orig['_apply_unit_action'](farm,private,idx,action,*args,**kw)
        if action and action[0]=='PLANT':self.plants.append({'step':self.step,'seat':self.farms[id(farm)],'unit':idx,'action':plain(action),'position':pos,
                                                          'consumed':dict(collections.Counter(before)-collections.Counter(private['seeds']))})
        return ret
    def animal_day(self,farm,day):
        before={(x,y):dict(t) for y,row in enumerate(farm['tiles']) for x,t in enumerate(row) if isinstance(t,dict) and t.get('animal')}
        ret=self.orig['_daily_refresh_animals'](farm,day)
        for (x,y),t in before.items():
            after=farm['tiles'][y][x]
            if not isinstance(after,dict) or not after.get('animal'):self.escapes.append({'step':self.step,'seat':self.farms[id(farm)],'animal':t['animal'],'position':[x,y],'tile_before':t})
        return ret
    def drop(self,private,*args,**kw):
        def total():return {a:private['shed'].get(a,0)+sum(i.get(a,0) for i in private['inventories']) for a in ANIMALS}
        before=total();ret=self.orig['_drop_inventories_to_shed'](private,*args,**kw);after=total()
        for a,n in before.items():
            if n>after[a]:self.animal_overflow.append({'step':self.step,'seat':self.privates[id(private)],'animal':a,'quantity':n-after[a]})
        return ret

def reconcile(game,trace,observer,official,frames):
    seat=game['candidate_seat'];proposals={(r['step'],r['orders_before']):r for r in observer.proposals if r['accepted_by_original_budget_check'] and r['order'][0] in OPS}
    checks=collections.defaultdict(list)
    for c in observer.checks:checks[(c['issued_step'],c['order_index'])].append(c)
    result=[]
    for step,pair in enumerate(trace['actions']):
        for index,order in enumerate(pair[seat].get('market',[])):
            if order[0] not in OPS:continue
            op=order[0];item=order[1] if len(order)>1 else 'land';n=order[2] if len(order)>2 else 1;key=(step,index)
            commits=[z for z in official.commits if (z['step'],z['seat'],z['order_index'])==(step,seat,index)]
            actual=sum(z['quantity'] for z in commits);target=proposals.get(key);cs=checks.get(key,[]);original=cs[0] if len(cs)==1 else None
            frame=frames[step];used=sum(z['consumed'].get(item,0) for z in official.plants if z['step']==step and z['seat']==seat)
            rawplants=sum(z[0]=='PLANT' and len(z)>1 and z[1]==item for z in [pair[seat].get('farmer',['PASS'])]+pair[seat].get('hands',[]) if z)
            escaped=sum(z['animal']==item for z in official.escapes if z['step']==step and z['seat']==seat)
            overflow=sum(z['quantity'] for z in official.animal_overflow if z['step']==step and z['seat']==seat and z['animal']==item)
            issues=[]
            if target is None or target.get('target') is None:issues.append('TARGET_UNOBSERVED')
            if target and target['order']!=order:issues.append('TARGET_PROPOSAL_ORDER_MISMATCH')
            if not commits:issues.append('ACTUAL_COMMIT_ATTEMPT_UNOBSERVED')
            if any(z['op']!=op or z['item']!=item for z in commits):issues.append('OFFICIAL_COMMIT_IDENTITY_MISMATCH')
            if step<718:
                if original is None:issues.append('ORIGINAL_NEXT_FRAME_CHECK_MISSING_OR_DUPLICATE')
                elif original['observed_step']!=step+1:issues.append('ORIGINAL_CHECK_NOT_NEXT_FRAME')
                elif original['order']!=order:issues.append('ORIGINAL_CHECK_ORDER_MISMATCH')
                elif original['got_in_original_code']!=actual:issues.append('ORIGINAL_CONFIRMATION_NOT_ACTUAL_COMMIT')
            if op=='BUY_SEED':net=frame['after']['seeds'].get(item,0)-frame['before']['seeds'].get(item,0);corrected=net+used
            elif op=='BUY_ANIMAL':net=frame['after']['assets'].get(item,0)-frame['before']['assets'].get(item,0);corrected=net+escaped+overflow
            else:net=frame['after']['land']-frame['before']['land'];corrected=net
            if corrected!=actual:issues.append('EXTERNAL_STATE_RECEIPT_NOT_CLOSED')
            gap=target.get('net_target_gap') if target else None;over_requested=max(0,n-gap) if gap is not None else None;over_actual=max(0,actual-gap) if gap is not None else None
            if over_requested or over_actual:issues.append('OVER_TARGET')
            result.append({'issued_step':step,'recorded_effect_step':step+1,'order_index':index,'order':order,'requested_quantity':n,'actual_committed_quantity':actual,
                           'actual_money_delta':sum(z['money_delta'] for z in commits),'target_capture':target,'net_target_gap':gap,
                           'over_target_requested_quantity':over_requested,'over_target_committed_quantity':over_actual,
                           'original_confirmation':original,'confirmation_source':'external_terminal_only_no_next_agent_call' if step==718 else 'original_confirm_orders_next_agent_call_plus_external_engine',
                           'raw_plant_requests':rawplants,'actual_seed_consumption':used,'animal_escapes_same_step':escaped,'animal_overflow_same_step':overflow,
                           'net_state_delta':net,'externally_corrected_receipt_quantity':corrected,'external_before':frame['before'],'external_after':frame['after'],
                           'issues':issues,'status':'PENDING' if issues else 'DIAGNOSTIC_COMPLETE'})
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--game-index',type=int,default=0);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    sys.dont_write_bytecode=True;run=args.run_dir.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'audit_manifest.json').exists():raise RuntimeError('拒绝覆盖已冻结采购审计')
    manifest=json.load(open(run/'run_manifest.json'));game=json.loads((run/'games.jsonl').read_text().splitlines()[args.game_index]);tracepath=Path(game['trace']['path'])
    assert game['status']=='DONE' and game['calls']==719 and game['backend']=='official','本原型只接收已有完整official动作带'
    assert sha(tracepath)==game['trace']['sha256'];trace=json.load(gzip.open(tracepath));assert len(trace['actions'])==719
    harness=Path(manifest['harness']['path']);assert sha(harness)==manifest['harness']['sha256'];h=load_module('receipt_original_harness',harness)
    for info in ('candidate','engine'):h.check_files(manifest[info])
    param_env={k:hashlib.sha256(v.encode()).hexdigest() for k,v in os.environ.items() if k in {'V15_PARAMS','V125_PARAMS'}}
    assert param_env==manifest['agent_parameter_environment_sha256'],'SOURCE_PARAMETER_ENV_MISMATCH'
    entry=Path(manifest['candidate']['entry']);observer=CandidateObserver(entry);make,rules,fast,engine=h.import_engines();assert engine['composite_sha256']==manifest['engine']['composite_sha256']
    guard_files=[MODEL/'evaluation/run_match.py',MODEL/'evaluation/run_match_v2.py',MODEL/'evaluation/summarize_g1.py',MODEL/'research/mechanism_analysis/analyze_trace.py']
    guards={str(p):sha(p) for p in guard_files}
    freeze={'schema':'v125-procurement-receipts-v2','started_at_utc':datetime.now(timezone.utc).isoformat(),'source_run':str(run),'source_game_index':args.game_index,
            'source_game_key':game['key'],'source_games_sha256':sha(run/'games.jsonl'),'source_trace':{'path':str(tracepath),'sha256':sha(tracepath)},
            'candidate':manifest['candidate'],'harness':manifest['harness'],'engine_composite_sha256':engine['composite_sha256'],
            'observer_script':{'path':str(Path(__file__).resolve()),'sha256':sha(__file__)},'guarded_files':guards,'workers':1,
            'evidence_role':'SAME_EXISTING_EPISODE_WITH_CANDIDATE_ACTION_REPRODUCTION_NOT_NEW_MATCH','requested_candidate_calls':719,
            'target_interpretation':{'animal':'原plan总资产目标','seed':'原market库存缓冲目标','land':observer.land_guard}}
    dump(out/'audit_manifest.json',freeze)
    e=h.Engine('official',trace['seed'],make,fast);seat=game['candidate_seat'];agent=h.Agent(manifest['candidate'],trace['seed'],seat)
    cfg=dict(e.g.configuration);cfg['seed']=None;initial=e.observe(seat);frames=[];compared=0;started=time.perf_counter()
    official=OfficialObserver(rules,e);failure=None
    try:
        with official:
            for step,pair in enumerate(trace['actions']):
                obs=e.observe(seat);before=assets(obs,seat);observer.step=step;official.step=step
                oldtrace=sys.gettrace();sys.settrace(observer.tracer)
                try:action=agent.call(obs,copy.deepcopy(cfg),10)
                finally:sys.settrace(oldtrace)
                difference=h.first_difference(action,pair[seat])
                if difference:raise RuntimeError(f'ACTION_MISMATCH step={step}: {difference}')
                compared+=1;e.step(copy.deepcopy(pair));frames.append({'step':step,'before':before,'after':assets(e.observe(seat),seat)})
        assert e.done() and e.rewards()==game['rewards'];assert h.snapshot([e.observe(s) for s in (0,1)])==game['terminal']
        original_diags=game.get('strategy_diagnostics',[None,None])[seat]
        raw_diagnostics=agent.diagnostics();diagnostics=plain(raw_diagnostics)
        with gzip.open(out/'reproduced_strategy_diagnostics.json.gz','wt') as f:json.dump(diagnostics,f,ensure_ascii=False)
        dump(out/'diagnostics_comparison.json',{'raw_python_equal':raw_diagnostics==original_diags,
             'raw_first_difference':h.first_difference(raw_diagnostics,original_diags),'json_normalized_equal':diagnostics==original_diags,
             'json_first_difference':h.first_difference(diagnostics,original_diags),
             'definition':'源games.jsonl已JSON序列化，tuple转list；比较前只做相同JSON归一化，不删字段。'})
        assert diagnostics==original_diags,'STRATEGY_DIAGNOSTICS_CHANGED_AFTER_JSON_NORMALIZATION'
        receipts=reconcile(game,trace,observer,official,frames)
        expected=game['action_audit']['actual_market_ledger'][seat]
        actual={op:collections.Counter() for op in OPS}
        for z in receipts:actual[z['order'][0]][z['order'][1] if len(z['order'])>1 else 'unlocked_quadrants']+=z['actual_committed_quantity']
        for op in OPS:assert dict(actual[op])==expected.get(op+'_qty',{}),(op,dict(actual[op]),expected.get(op+'_qty'))
        dump(out/'receipts.json',receipts);dump(out/'initial_observation_for_microcases.json',initial)
        dump(out/'summary.json',{'status':'DIAGNOSTIC_COMPLETE' if all(not z['issues'] for z in receipts) else 'PENDING','source_game_key':game['key'],
             'orders':len(receipts),'requested_units':sum(z['requested_quantity'] for z in receipts),'actual_committed_units':sum(z['actual_committed_quantity'] for z in receipts),
             'original_next_frame_checks':sum(z['original_confirmation'] is not None for z in receipts),'terminal_external_only_orders':sum(z['issued_step']==718 for z in receipts),
             'issues':dict(collections.Counter(issue for z in receipts for issue in z['issues'])),'over_target_requested_units':sum(z['over_target_requested_quantity'] or 0 for z in receipts),
             'over_target_committed_units':sum(z['over_target_committed_quantity'] or 0 for z in receipts),'raw_plant_request_vs_consumption_mismatch_order_count':sum(z['order'][0]=='BUY_SEED' and z['raw_plant_requests']!=z['actual_seed_consumption'] for z in receipts),
             'animal_loss_overlap_buy_orders':sum(z['order'][0]=='BUY_ANIMAL' and (z['animal_escapes_same_step'] or z['animal_overflow_same_step'])>0 for z in receipts),
             'candidate_calls':len(agent.latencies),'action_comparisons':compared,'candidate_actions_equal_saved_trace':True,'strategy_diagnostics_equal_source':True,
             'terminal_saved_snapshot_equal_source':True,'actual_purchase_totals_equal_source':True,'cash':e.rewards(),'elapsed_seconds':time.perf_counter()-started,
             'qualification':'已打开旧局的逐笔诊断，不自动授予G1；静态土地上限与种子缓冲目标的含义必须保留。'})
    except Exception as exc:
        failure=f'{type(exc).__name__}: {exc}';dump(out/'failure.json',{'error':failure,'candidate_calls':len(agent.latencies),'actions_compared':compared,'new_independent_matches':0})
    finally:
        for name,rows in [('candidate_confirm_calls',observer.calls),('candidate_original_checks',observer.checks),('candidate_plan_returns',observer.plans),('candidate_fixed_order_calls',observer.proposals),
                          ('official_unit_commits',official.commits),('official_plant_consumption',official.plants),('official_animal_escapes',official.escapes),('official_animal_overflow',official.animal_overflow),('external_state_frames',frames)]:
            with gzip.open(out/(name+'.jsonl.gz'),'wt') as f:
                for z in rows:f.write(json.dumps(z,ensure_ascii=False)+'\n')
        for path,value in guards.items():assert sha(path)==value,('GUARDED_FILE_CHANGED',path)
        h.check_files(manifest['candidate']);h.check_files(manifest['engine'])
    if failure:raise RuntimeError(failure)
    dump(out/'validation.json',{'candidate_file_and_guarded_files_unchanged':True,'source_trace_sha_verified':True,'action_comparisons':compared,'candidate_calls':len(agent.latencies),
                              'new_independent_matches':0,'all_original_confirm_calls_observed':len(observer.calls)==719,'source_games_unchanged':sha(run/'games.jsonl')==freeze['source_games_sha256'],
                              'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps(json.load(open(out/'summary.json')),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
