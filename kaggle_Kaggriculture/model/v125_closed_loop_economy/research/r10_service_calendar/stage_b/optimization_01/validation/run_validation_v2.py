"""P1预登记有限控制。未获得根release时拒绝定义加载候选。"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def typed(v):
    """保留原类型、dict插入序、tuple/set/Counter及浮点精确值，不丢字段。"""
    name=type(v).__module__+'.'+type(v).__qualname__
    if v is None:return [name,None]
    if isinstance(v,bool):return [name,v]
    if isinstance(v,int):return [name,str(v)]
    if isinstance(v,float):return [name,v.hex()]
    if isinstance(v,str):return [name,v]
    if isinstance(v,dict):return [name,[[typed(k),typed(x)]for k,x in v.items()]]
    if isinstance(v,(list,tuple)):return [name,[typed(x)for x in v]]
    if isinstance(v,(set,frozenset)):return [name,sorted([typed(x)for x in v],key=lambda x:json.dumps(x,sort_keys=True))]
    raise TypeError('未登记的证据类型:'+name)


def fingerprint(v):return hashlib.sha256(json.dumps(typed(v),ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def differences(a,b,path='$'):
    out=[]
    def add(p,x,y):out.append({'path':p,'P0':typed(x),'P1':typed(y)})
    def walk(x,y,p):
        if type(x) is not type(y):add(p,x,y);return
        if isinstance(x,dict):
            xkeys={fingerprint(k):k for k in x};ykeys={fingerprint(k):k for k in y}
            if list(xkeys)!=list(ykeys):add(p+'.@ordered_keys',list(x),list(y))
            for k in xkeys.keys()|ykeys.keys():
                if k in xkeys and k in ykeys:walk(x[xkeys[k]],y[ykeys[k]],p+'['+repr(xkeys[k])+']')
                elif k in xkeys:out.append({'path':p+'['+repr(xkeys[k])+']','P0':typed(x[xkeys[k]]),'P1_missing':True})
                else:out.append({'path':p+'['+repr(ykeys[k])+']','P0_missing':True,'P1':typed(y[ykeys[k]])})
        elif isinstance(x,(list,tuple)):
            if len(x)!=len(y):add(p+'.@length',len(x),len(y))
            for i in range(min(len(x),len(y))):walk(x[i],y[i],p+'['+str(i)+']')
            for i in range(min(len(x),len(y)),max(len(x),len(y))):
                out.append({'path':p+'['+str(i)+']','P0':typed(x[i]) if i<len(x) else None,'P1':typed(y[i]) if i<len(y) else None,'missing_side':'P0' if i>=len(x) else 'P1'})
        elif typed(x)!=typed(y):add(p,x,y)
    walk(a,b,path)
    return out


class CallDeadline(Exception):pass


def bounded(fn,args,seconds):
    def expired(signum,frame):raise CallDeadline('预登记诊断保护超时'+str(seconds)+'秒')
    old=signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,seconds)
    start=time.perf_counter()
    try:return fn(*args),time.perf_counter()-start
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)


class NativeReferences:
    """纯接口专用只读profile；完整economic计时不启用它。"""
    def __init__(self,ns,counts):
        self.codes={ns['_r10_calendar_compiler_compile_day_problem'].__code__:'compile_day_problem',
                    ns['_r10_scheduler_schedule_day'].__code__:'native_scheduler',
                    ns['_r10_checker_check_day'].__code__:'native_checker'}
        self.counts=counts;self.refs=[]
    def callback(self,frame,event,arg):
        name=self.codes.get(frame.f_code)
        if name is None:return
        if event=='call':self.counts['pure_'+name+'_calls']+=1
        if event=='return' and name in ('compile_day_problem','native_scheduler') and isinstance(arg,dict):
            self.refs.append({'kind':name,'reference':arg,'snapshot':deepcopy(arg)})
    def __enter__(self):self.old=sys.getprofile();sys.setprofile(self.callback);return self
    def __exit__(self,*args):sys.setprofile(self.old)


class Suite:
    def __init__(self,freeze,out):
        self.freeze,self.out=freeze,out;self.counts=Counter();self.results=[];self.errors=[]
        self.live_results={};self.economic={};self.performance={};self.active=None

    def check(self,name,condition,detail=None):
        self.active.setdefault('checks',{})[name]=bool(condition)
        if not condition:
            self.active['first_difference']={'check':name,'detail':detail};raise AssertionError(name)

    def verify(self):
        for p,value in self.freeze['files'].items():
            if sha(p)!=value:raise ValueError('SOURCE_SHA_DRIFT:'+p)

    def namespace(self,label):
        self.verify();p=Path(self.freeze['sources'][label]);self.counts['module_definition_loads']+=1
        ns={'__name__':'_p1_control_'+label+'_'+str(self.counts['module_definition_loads']),'__file__':str(p)}
        exec(compile(p.read_bytes(),str(p),'exec'),ns)
        self.check('fresh_module_state',ns['_STATES']=={})
        self.check('original_parameters_exact',ns['PARAMS']==self.freeze['expected_params'])
        self.active['module']={'path':str(p),'sha256':sha(p),'candidate_id':ns['CANDIDATE_ID'],'parameters':deepcopy(ns['PARAMS'])}
        return ns

    def save(self):
        if self.active is None:return
        p=self.out/(self.active['id']+'.json.gz')
        with gzip.open(p,'wt') as f:json.dump(self.active,f,ensure_ascii=False,allow_nan=False)
        self.results.append({'id':self.active['id'],'path':str(p),'sha256':sha(p),'checks':self.active.get('checks',{}),'error':self.active.get('error')})
        self.active=None

    def failure(self,exc):
        e={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        self.active['error']=e;self.errors.append({'id':self.active['id'],**e})

    def pure(self,label,fixture):
        self.active={'id':label+'_pure_definition','checks':{}};ns=self.namespace(label)
        x=fixture['interface_case'];cals=[]
        for pos in x['positions']:
            self.counts['pure_calendar_calls']+=1
            cals.append(ns['_r10_calendar_compiler_project_calendar_with_services'](deepcopy(x['tile']),x['today'],x['hour'],tuple(pos)))
        self.counts['pure_aggregate_calls']+=1
        aggregate=ns['_r10_route_admission_aggregate_calendars'](cals)
        days=lambda d:{int(k):deepcopy(v) for k,v in d.items()}
        labor=deepcopy(x['labor']);labor['cash_by_day']=days(labor['cash_by_day']);labor['capacity_by_day']=days(labor['capacity_by_day'])
        funding=deepcopy(x['funding_feed'])
        for k in ('buys_by_day','stock_by_day','cash_by_day'):funding[k]=days(funding[k])
        portfolio={'calendars':cals,'coverage_asset_ids':[c['asset_id']for c in cals],'legacy_aggregate':aggregate,'workload':deepcopy(aggregate['work']),
                   'labor':labor,'funding_requirements':days(x['funding_requirements']),'funding_feed':funding,
                   'startup_fallback_days':[],'pending_animal_units':{},'conditional_prior_product_sales':True}
        self.check('known_work336_capacity285',portfolio['workload'][29]==336 and portfolio['labor']['capacity_by_day'][29]==285)
        self.active['portfolio']=typed(portfolio);self.save()
        common_cache=None;cold_passed=False
        for name in x['registered_cases']:
            self.active={'id':label+'_interface_'+name,'checks':{},'scope':'纯接口profile不作性能证据'}
            try:
                self.verify()
                if name=='default_cache_hit' and not cold_passed:
                    self.active['skipped']='PENDING_COLD_CASE_FAILED';continue
                private=deepcopy(x['private']);base=deepcopy(portfolio);trial=deepcopy(portfolio)
                if name!='default_cache_hit':
                    self.counts['pure_cache_constructions']+=1
                    cache=ns['_r10_route_admission_PlanRouteCache'](x['token'],x['today'],private)
                else:cache=common_cache
                before=deepcopy((base,trial,private));cache_before=deepcopy(cache.entries);hook_rows=[]
                native_schedule=ns['_r10_scheduler_schedule_day'];native_check=ns['_r10_checker_check_day']
                def custom_schedule(problem,n_hands):
                    self.counts['pure_custom_schedule_calls']+=1
                    cert=native_schedule(problem,n_hands)
                    problem['start_shed']['WHEAT']=999
                    hook_rows.append({'name':'schedule','received_P_mutated_to':999})
                    return cert
                def custom_check(problem,certificate):
                    self.counts['pure_custom_check_calls']+=1
                    result=native_check(problem,certificate)
                    problem['start_shed']['WHEAT']=999
                    certificate['n_hands']=999;certificate['hire_cost']=0
                    hook_rows.append({'name':'check','received_P_mutated_to':999,'received_C_n_hands_mutated_to':999,'received_C_hire_cost_mutated_to':0})
                    return result
                watch=NativeReferences(ns,self.counts)
                self.counts['pure_route_calls']+=1
                with watch:
                    result=ns['_r10_route_admission_route_admission'](base,trial,current_day=x['today'],observed_private=private,plan_token=x['token'],cache=cache,
                        schedule=custom_schedule if name=='custom_schedule_only' else None,
                        check=custom_check if name=='custom_check_only' else None,implementation_ids=self.freeze['implementation_ids'])
                self.active.update(result=typed(result),cache=typed(cache.entries),hook_events=hook_rows,
                    external_reference_snapshots=[{'kind':r['kind'],'snapshot':typed(r['snapshot']),'after_route':typed(r['reference'])}for r in watch.refs])
                self.check('baseline_trial_private_unchanged',not differences(before,(base,trial,private)))
                self.check('route_full_success',result['labor_feasible_after_routes'] is True and result['route_feasibility_by_day']=={29:True},typed(result))
                self.check('external_original_P_C_unmodified',all(not differences(r['snapshot'],r['reference']) for r in watch.refs))
                if name=='default_cache_hit':
                    self.check('hit_no_solver',result['cache_hits']==1 and result['scheduler_calls']==result['checker_calls']==0)
                    self.check('hit_cache_values_unchanged',not differences(cache_before,cache.entries))
                elif name.startswith('custom_'):self.check('custom_hook_executed_once',len(hook_rows)==1)
                cache_snapshot=deepcopy(cache.entries);result_snapshot=deepcopy(result)
                for r in watch.refs:
                    if r['kind']=='compile_day_problem':r['reference']['start_shed']['WHEAT']=888
                    else:r['reference']['n_hands']=888;r['reference']['hire_cost']=0
                self.check('external_alias_mutation_does_not_reach_cache',not differences(cache_snapshot,cache.entries))
                alias_changes=differences(result_snapshot,result,'result_before_and_after_external_mutation')
                self.active['result_reverse_alias_changes']=alias_changes
                self.active['result_after_external_mutation']=typed(result)
                self.check('external_alias_mutation_does_not_reach_baseline',not differences(before,(base,trial,private)))
                # 原P0 evidence直接持有部分P字段；比较该别名行为是否原样保持，不虚构原本不存在的隔离。
                self.live_results[(label,name)]=(result_snapshot,cache_snapshot,deepcopy(alias_changes))
                if name=='default_cold':common_cache=cache;cold_passed=True
            except BaseException as exc:self.failure(exc)
            finally:self.save()

    def full_economic(self,label,fixture):
        self.active={'id':label+'_full_economic_once','checks':{},'profile':False,'purpose':'P1完整等价参照，不覆盖旧10s完整入口失败'}
        obs=deepcopy(fixture['economic_case']['observation']);st=None;plan=None
        try:
            ns=self.namespace(label);self.counts['new_state_calls']+=1;st=ns['new_state'](deepcopy(obs))
            before=deepcopy(obs);self.counts['internal_economic_calls']+=1;start=time.perf_counter()
            try:
                plan,elapsed=bounded(ns['economic_plan_prefix'],(obs,st),fixture['economic_timeout_seconds'])
                self.active.update(returned=True,seconds=elapsed,over_1s=elapsed>1,plan=typed(plan),state=typed(st),plan_sha256=fingerprint(plan),state_sha256=fingerprint(st))
                self.economic[label]=(deepcopy(plan),deepcopy(st))
            finally:
                self.active.setdefault('seconds',time.perf_counter()-start)
                self.active.setdefault('over_1s',self.active['seconds']>1)
                self.active.setdefault('returned',False)
                self.active['state_after_attempt']=typed(st)
                self.active['observation_unchanged']=not differences(before,obs)
                self.performance[label]={k:self.active[k] for k in ('returned','seconds','over_1s','observation_unchanged')}
        except BaseException as exc:self.failure(exc)
        finally:self.save()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',type=Path,required=True);a=ap.parse_args()
    raw=a.freeze.read_bytes();f=json.loads(raw)
    if f.get('schema')!='r10-p1-validation-freeze-v1' or f.get('root_execution_release') is not True:raise SystemExit('ROOT_RELEASE_REQUIRED')
    for p,v in f['files'].items():
        if sha(p)!=v:raise SystemExit('SOURCE_SHA_MISMATCH:'+p)
    assert f['files'].get(str(Path(__file__).resolve()))==sha(__file__)
    out=Path(f['output_path']);out.mkdir(parents=True,exist_ok=False)
    fixture=json.loads(Path(f['fixture_path']).read_bytes());s=Suite(f,out);top_error=None
    try:
        for label in ('P0','P1'):s.pure(label,fixture)
        for label in ('P0','P1'):s.full_economic(label,fixture)
    except BaseException as exc:
        top_error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        if s.active:s.failure(exc);s.save()
    pure={}
    for name in fixture['interface_case']['registered_cases']:
        both=all((label,name)in s.live_results for label in ('P0','P1'))
        ds=differences(s.live_results[('P0',name)],s.live_results[('P1',name)]) if both else None
        pure[name]={'both_complete':both,'exact_pre_mutation_result_cache_and_alias_effect_equal':both and not ds,
                    'exact_result_and_cache_equal':both and not ds,'differences':ds}
    both=all(label in s.economic for label in ('P0','P1'))
    ds=differences(s.economic['P0'],s.economic['P1'],'plan_and_state') if both else None
    performance_pass=all(s.performance.get(label,{}).get('returned') and not s.performance[label]['over_1s'] for label in ('P0','P1'))
    p1_performance_pass=bool(s.performance.get('P1',{}).get('returned') and not s.performance['P1']['over_1s'])
    drift=[p for p,v in f['files'].items() if sha(p)!=v]
    if a.freeze.read_bytes()!=raw:drift.append(str(a.freeze))
    equivalence_pass=not bool(s.errors or top_error or drift or not both or ds or not all(r['exact_result_and_cache_equal']for r in pure.values()))
    result={'schema':'r10-p1-validation-result-v2','created_at_utc':datetime.now(timezone.utc).isoformat(),'freeze_sha256':hashlib.sha256(raw).hexdigest(),
        'counts':dict(s.counts),'records':s.results,'errors':s.errors,'top_error':top_error,'source_drift':drift,
        'interface_equivalence':pure,'unprofiled_internal_performance':s.performance,'both_internal_calls_within_1s':performance_pass,
        'P1_internal_call_within_1s':p1_performance_pass,'equivalence_and_source_integrity_pass':equivalence_pass,
        'status':'EQUIVALENCE_OR_SOURCE_FAILURE' if not equivalence_pass else 'P1_TIME_THRESHOLD_FAILED' if not p1_performance_pass else 'P1_BOUNDED_CONTROL_PASSED_NOT_QUALIFICATION',
        'full_economic_equivalence':{'both_returned':both,'exact_full_plan_and_state_equal':both and not ds,'differences':ds,
             'missing_outputs':[label for label in ('P0','P1')if label not in s.economic]},
        'whole_agent_calls':0,'official_calls':0,'new_complete_matches':0,
        'scope':'一次性内部经济等价/耗时与纯接口隔离；120s不放宽1s，非正式候选或金牌裁决。'}
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'summary':str(out/'summary.json'),'counts':dict(s.counts),'full_both_returned':both,'full_exact_equal':both and not ds,
        'error_count':len(s.errors),'source_drift':drift},ensure_ascii=False))
    return int(not equivalence_pass or not p1_performance_pass)


if __name__=='__main__':raise SystemExit(main())
