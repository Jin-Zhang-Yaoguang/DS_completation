"""阶段A证书官方短执行与冻结R9兑现比较，不生成任何新完整比赛。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
MODEL=next(p for p in HERE.parents if p.name=='v125_closed_loop_economy')
sys.path.insert(0,str(MODEL/'research/r4_contract_design'))
import test_microcases as common
engine=common.scaffold.engine
from scheduler import canonical_sha,generate_schedule,problem_from_observation
from checker import check_certificate

POSITIONS=[(3,4),(3,3),(3,2),(3,1),(2,1),(1,1)]
EXPECTED='e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0'
R9=MODEL/'candidates/V125-R9/main.py'
assert hashlib.sha256(R9.read_bytes()).hexdigest()==EXPECTED

def environment(seat,multiple=False):
    env=common.empty_env(seat,2,0);f=env.state[0].observation.farms[seat]
    f['farmer']=[4,4];f['money']=0;f['hands']=[[5,4]]if multiple else [];f['hires_today']=int(multiple)
    f['tiles']=[[None if x<5 and y<5 else 'LOCKED'for x in range(10)]for y in range(10)]
    for x,y in POSITIONS:
        f['tiles'][y][x]=engine.RULES._new_plant('MELON',0,0)
        f['tiles'][y][x]['watered_today']=False;f['tiles'][y][x]['consecutive_unwatered']=1
    env.state[seat].observation.private['inventories']=[{}for _ in range(1+int(multiple))]
    return env

def load_r9():
    spec=importlib.util.spec_from_file_location('frozen_r9_stage_a',R9);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def problem_for(env,seat):
    o=engine.observed(env,seat);units=list(range(1+len(o['farms'][seat]['hands'])))
    return problem_from_observation(o,POSITIONS,o['step']+17,units,{u:(4,4)for u in units})

checks={};runs=[];candidate_calls=0;official_steps=0
for seat in (0,1):
    outcomes=[]
    for mode in ('certificate','frozen_r9'):
        env=environment(seat);initial=engine.observed(env,seat);problem,provenance=problem_for(env,seat)
        cert=generate_schedule(problem);validation=check_certificate(problem,cert)
        checks[f'certificate_valid_s{seat}_{mode}']=validation['valid']
        if not validation['valid']:raise RuntimeError(validation)
        by_step={}
        for action in cert['actions']:by_step.setdefault(action['step'],{})[action['unit']]=action['action']
        mod=load_r9()if mode=='frozen_r9'else None
        rows=[];completed={};first_deviation=None
        for step in range(problem['start_step'],problem['end_step']+1):
            before=engine.observed(env,seat)
            expected={'farmer':by_step[step][0],'hands':[],'market':[]}
            action=mod.agent(before)if mod else deepcopy(expected)
            if mod:candidate_calls+=1
            if first_deviation is None and action!=expected:
                first_deviation={'step':step,'expected':expected,'actual':deepcopy(action)}
            pair=[deepcopy(engine.PASS),deepcopy(engine.PASS)];pair[seat]=deepcopy(action)
            engine.official_step(env,pair);official_steps+=1
            after=engine.observed(env,seat)
            for service in problem['services']:
                x,y=service['position'];a=before['farms'][seat]['tiles'][y][x];b=after['farms'][seat]['tiles'][y][x]
                if not a.get('watered_today') and b.get('watered_today'):
                    completed[service['service_id']]={'decision_step':step,'position':[x,y]}
            rows.append({'step':step,'expected_certificate':expected,'actual_action':deepcopy(action),
                         'farmer_before':before['farms'][seat]['farmer'],'farmer_after':after['farms'][seat]['farmer'],
                         'actual_completed_so_far':deepcopy(completed)})
        final=engine.observed(env,seat)
        all_done=set(completed)=={s['service_id']for s in problem['services']}
        deadlines=all(completed[s['service_id']]['decision_step']<=s['deadline_step']for s in problem['services']if s['service_id']in completed)
        returned=final['farms'][seat]['farmer']==[4,4]
        if mode=='certificate':
            checks[f'official_certificate_water_all_s{seat}']=all_done and deadlines
            checks[f'official_certificate_return_s{seat}']=returned
            checks[f'official_certificate_exact18_s{seat}']=len(rows)==18 and sum(a['action'][0]=='WATER'for a in cert['actions'])==6
        outcomes.append({'mode':mode,'seat':seat,'problem':problem,'provenance':provenance,'certificate':cert,'checker':validation,
                         'initial_observation':initial,'rows':rows,'actual_completed_services':completed,'actual_all_services_completed':all_done,
                         'actual_deadlines_met':deadlines,'actual_return_met':returned,'first_action_deviation':first_deviation,
                         'execution_relation':'ACTUAL_OFFICIAL_EFFECTS; certificate schedule is not itself a receipt',
                         'final_observation':final})
    checks[f'paired_same_initial_observation_s{seat}']=outcomes[0]['initial_observation']==outcomes[1]['initial_observation']
    runs.extend(outcomes)

# 同一已到场的双工人问题；不虚构HIRE或随机出生点。
env=environment(0,True);initial=engine.observed(env,0);problem,provenance=problem_for(env,0);cert=generate_schedule(problem)
validation=check_certificate(problem,cert);checks['two_existing_workers_certificate_valid']=validation['valid']
assert validation['valid'];by_step={}
for entry in cert['actions']:by_step.setdefault(entry['step'],{})[entry['unit']]=entry['action']
rows=[]
for step in range(problem['start_step'],problem['end_step']+1):
    act={'farmer':by_step[step][0],'hands':[by_step[step][1]],'market':[]}
    pair=[act,deepcopy(engine.PASS)];engine.official_step(env,pair);official_steps+=1
    rows.append({'step':step,'actual_action':act})
final=engine.observed(env,0)
checks['two_existing_workers_official_water_complete']=all(final['farms'][0]['tiles'][y][x]['watered_today']for x,y in POSITIONS)
checks['two_existing_workers_official_return']=final['farms'][0]['farmer']==[4,4]and final['farms'][0]['hands']==[[4,4]]
runs.append({'mode':'two_existing_workers_certificate','seat':0,'initial_observation':initial,'problem':problem,'provenance':provenance,
             'certificate':cert,'checker':validation,'rows':rows,'final_observation':final})

# 生成器自身的负控制；完整证书变异由独立checker测试承担。
base,provenance=problem_for(environment(0),0)
short=deepcopy(base);short['end_step']-=1
for u in short['units']:u['available_until']-=1
for s in short['services']:s['deadline_step']-=1
checks['generator_17_slots_no_certificate']=generate_schedule(short)['status']=='NO_CERTIFICATE'
far=deepcopy(base);far['units'][0]['start']=[9,9]
checks['generator_far_start_no_free_warehouse']=generate_schedule(far)['status']=='NO_CERTIFICATE'
late=deepcopy(base)
for s in late['services']:s['deadline_step']=base['start_step']
checks['generator_early_deadline_no_certificate']=generate_schedule(late)['status']=='NO_CERTIFICATE'
before=canonical_sha(base);generate_schedule(base);checks['generator_does_not_mutate_problem']=canonical_sha(base)==before
checks['adapter_rejects_unobserved_worker']=False
try:problem_from_observation(engine.observed(environment(0),0),POSITIONS,65,[1])
except ValueError:checks['adapter_rejects_unobserved_worker']=True
checks['adapter_rejects_already_watered']=False
env=environment(0);env.state[0].observation.farms[0]['tiles'][4][3]['watered_today']=True
try:problem_for(env,0)
except ValueError:checks['adapter_rejects_already_watered']=True

result={'created_at_utc':datetime.now(timezone.utc).isoformat(),'schema':'r10-stage-a-official-controls-v1','checks':checks,
        'passed':sum(checks.values()),'total':len(checks),'runs':runs,'frozen_r9_sha256':EXPECTED,
        'scheduler_sha256':hashlib.sha256((HERE/'scheduler.py').read_bytes()).hexdigest(),
        'checker_sha256':hashlib.sha256((HERE/'checker.py').read_bytes()).hexdigest(),
        'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'frozen_r9_candidate_calls':candidate_calls,'certificate_candidate_calls':0,'official_short_steps':official_steps,
        'official_initializations':5,'fixture_seed':'1250501 existing fixed artificial microfixture, no new evaluation seed',
        'new_complete_matches':0,'new_replays_opened':False,'candidate_admission_modified':False}
path=HERE/('official_controls_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'result':str(path),'passed':result['passed'],'total':result['total'],'failed':[k for k,v in checks.items()if not v],
                  'official_short_steps':official_steps,'frozen_r9_calls':candidate_calls,
                  'r9_realization':[{'seat':r['seat'],'completed':r['actual_all_services_completed'],'return':r['actual_return_met'],
                                      'first_deviation':r['first_action_deviation']}for r in runs if r['mode']=='frozen_r9']},ensure_ascii=False))
