"""纯数据合成边界+既有R8文件只读schema验证；新比赛/候选/引擎均为0。"""
import copy,gzip,hashlib,importlib.util,json
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load(P/'assess_early_sales_v2.py','r9_test_module');checks=[]
def ok(name,value):assert value,name;checks.append(name)
def rows(parent=100,new=120):return [{'candidate_id':v,'opponent':o,'seed':s,'seat':t,'source_key':str((v,o,s,t)),'first_sale':{'status':'NUMERIC_COMPLETE','early_days_0_9_cash':parent if v=='V125-R8' else new,'early_days_0_9_units':1}} for v,o,s,t in sorted(m.EXPECTED)]
r=rows();a=m.assess(r);ok('exact_20percent_integer_boundary',a['primary_mechanism_numeric_threshold_pass'])
ok('below_20percent_fails',not m.assess(rows(new=119))['primary_mechanism_numeric_threshold_pass'])
r=rows();[x['first_sale'].update(early_days_0_9_cash=0) for x in r if x['seed']==1950905901];ok('complete_zero_sale_game_retained',m.assess(r)['primary_mechanism_numeric_threshold_pass'])
a=m.assess(rows(new=0));ok('candidate_zero_is_numeric_failure',a['data_integrity_pass'] and a['groups'][0]['status']=='NUMERIC_COMPLETE' and a['groups'][0]['primary_numeric_threshold_pass'] is False)
a=m.assess(rows(parent=0,new=0));ok('parent_zero_is_pending_not_auto_pass',a['groups'][0]['status']=='PENDING' and a['groups'][0]['primary_numeric_threshold_pass'] is None)
r=rows();[x['first_sale'].update(early_days_0_9_cash=90 if x['seat']==0 else 150) for x in r if x['candidate_id']=='V125-R9'];a=m.assess(r);ok('seat_decline_cannot_be_pooled_away',a['groups'][0]['at_least_20_percent'] is True and not a['primary_mechanism_numeric_threshold_pass'])
for label,changed in [('missing',rows()[:-1]),('duplicate',rows()+[rows()[0]])]:ok(label+'_cell_failclosed',not m.assess(changed)['data_integrity_pass'])
r=rows();r[0]['seed']=1950905801;ok('wrong_seed_failclosed',not m.assess(r)['data_integrity_pass'])
r=rows();r[0]['first_sale']['status']='PENDING_PROVENANCE';ok('provenance_pending_blocks',not m.assess(r)['data_integrity_pass'])
for value in [True,-1,0.5,float('nan'),None]:
 r=rows();r[0]['first_sale']['early_days_0_9_cash']=value;ok('invalid_cash_'+repr(value),not m.assess(r)['data_integrity_pass'])
# 合成末时雇工：1块土地+首位手工资1；日终hands=0依旧付费。
before={'step':239,'day':9,'hour':23,'money':2000,'quadrants':['NW'],'hands':0};after={'step':240,'day':10,'hour':0,'farms':[{'money':999,'unlocked_quadrants':['NW','NE'],'hands':[]},{}]}
a=m.boundary_atomic_costs([before],[after],[['HIRE'],['BUY_LAND']],[],0,{})
ok('hour23_paid_hire_survives_eod_reset_in_cash_accounting',a['HIRE']==1 and a['BUY_LAND']==1000 and a['post_eod_hand_count']==0)
x=copy.deepcopy(after);x['farms'][0]['money']=1999;x['farms'][0]['unlocked_quadrants']=['NW'];a=m.boundary_atomic_costs([before],[x],[['HIRE']],[],0,{})
ok('hour23_hire_only_cost_one',a['HIRE']==1 and a['BUY_LAND']==0)
x=copy.deepcopy(after);x['farms'][0]['money']=998;a=m.boundary_atomic_costs([before],[x],[['HIRE'],['BUY_LAND']],[],0,{})
ok('inconsistent_hire_cash_is_pending',a['status']=='PENDING' and a['HIRE'] is None)
a=m.boundary_atomic_costs([before],[],[],[],0,{});ok('missing_endpoint_is_pending',a['status']=='PENDING')
x=copy.deepcopy(after);x['farms'][0]['money']=999;a=m.boundary_atomic_costs([before],[x],[['BUY_LAND']],[],0,{})
ok('unrequested_cash_cost_cannot_be_assigned_to_hire',a['status']=='PENDING')
x=copy.deepcopy(after);x['farms'][0]['money']=1029;events=[{'op':'SELL','quantity':2,'price':20},{'op':'BUY_SEED','quantity':1,'price':10}];a=m.boundary_atomic_costs([before],[x],[['HIRE'],['BUY_LAND']],events,0,{})
ok('boundary_sale_and_purchase_cash_closed',a['HIRE']==1 and a['BUY_LAND']==1000)
# 冻结官方rule只读指纹。只载入既有R8完整块的纯数据 assessor，不调用任何候选。
h=load(ROOT/'evaluation/assess_paired_development.py','frozen_strength_for_r9_test');plan,snap,issues,files=h.read_plan(ROOT/'research/r8_terminal_net_selection/frozen_bundle.json');baseline=h.evaluate(plan,snap,issues);ok('existing_R8_36_schema_integrity_passes',baseline['data_integrity_pass'])
for name,change in [('not_DONE',lambda x:x[0]['games'][0].update(status='ERROR')),('calls718',lambda x:x[0]['games'][0].update(calls=718)),('wrong_entry_SHA',lambda x:x[0]['manifest']['candidate'].update(entry_sha256='0'*64)),('missing_game',lambda x:x[0]['games'].pop()),('duplicate_game',lambda x:x[0]['games'].append(copy.deepcopy(x[0]['games'][0]))),('parity_null',lambda x:x[0]['games'][0].update(parity_pass=None)),('slow_call',lambda x:x[0]['games'][0]['agents'][0].update(calls_over_1s=1))]:
 t=copy.deepcopy(snap);change(t);ok('frozen_integrity_rejects_'+name,not h.evaluate(plan,t,issues)['data_integrity_pass'])
# 单局旧R8 schema：0..239准确窗口，没有新比赛。
run=ROOT/'evaluation/r8_pass_diagnostic_s0';game=json.loads((run/'games.jsonl').read_text().splitlines()[0]);audit=ROOT/'research/r8_terminal_net_selection/opened_trace_audit/r8_pass_s0_mechanism';events=[json.loads(x) for x in gzip.open(audit/'events.jsonl.gz','rt')];trace=json.load(gzip.open(game['trace']['path'],'rt'));daily=json.load(gzip.open(audit/'daily_states.json.gz','rt'));rm=json.loads((run/'run_manifest.json').read_text());cost=m.early_costs(game,events,trace,daily,rm['configuration'])
ok('opened_R8_cost_schema_full_window',cost['window_decisions']==[0,239] and all(x['status']=='NUMERIC_COMPLETE' for x in cost['land_and_hire_cash'].values()))
for p,hv in files.items():assert m.sha(p)==hv
# 真实24条已存首卖产物：只统一v3 JSON表现，所有字段仍严格比较。
frozen_first=load(ROOT/'research/r8_terminal_net_selection/summarize_first_produced_sale_v3.py','r9_first_v3_reproduction_test')
all_first=json.loads((ROOT/'research/r9_cash_prefix/fresh_mechanism_audit/all_24_first_sale/first_sale.json').read_text())['games']
assert len(all_first)==24
reproduced=[]
for saved in all_first:
 verified,fp=frozen_first.audit(saved['audit_directory']);assert m.serialized_evidence(verified)==saved;reproduced.append((verified,saved))
ok('all_24_real_v3_json_forms_strictly_equal',len(reproduced)==24)
verified,saved=reproduced[0];altered=copy.deepcopy(saved);day=next(iter(altered['daily']));altered['daily'][day]['cash']+=1
ok('changed_daily_cash_still_rejected',m.serialized_evidence(verified)!=altered)
altered=copy.deepcopy(saved);altered['first_sale_items']={}
ok('changed_first_basket_still_rejected',m.serialized_evidence(verified)!=altered)
ok('primary_complete_result_unchanged_vs_v1',m.assess(rows())==load(P/'assess_early_sales.py','original_r9_primary_only').assess(rows()))
result={'all_pass':True,'checks':checks,'check_count':len(checks),'aggregator_sha256':m.sha(P/'assess_early_sales_v2.py'),'candidate_calls':0,'engine_steps':0,'new_independent_matches':0,'synthetic_only_mutations':True,'readonly_schema_sources':'旧R8已打开诊断与已完成36开发块用于30项原测试；另只读复核R9阶段已经保存的24条R8/R9首卖证据，不调用候选或引擎。','opened_R8_early_cost_schema':cost}
(P/'validation_v2_final.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print(json.dumps({'all_pass':True,'checks':len(checks),'source_sha256':result['aggregator_sha256'],'old_R8_cost':cost},ensure_ascii=False,indent=2))
