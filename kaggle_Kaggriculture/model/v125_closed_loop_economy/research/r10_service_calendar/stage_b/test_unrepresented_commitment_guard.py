"""只提取两个接入纯helper；不加载/调用完整原型。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import ast,copy,hashlib,json
import route_admission as route
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
helper=ast.parse((HERE/'integration_helpers.py').read_text())
names={'_r10_integration_note_unrepresented_commitment','_r10_integration_rows'}
functions=[n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name in names]
actual_calls=[]
def actual_calendars(ctx):
    actual_calls.append(True)
    return []
ns={'_r10_integration_copy':copy,'_r10_route_admission__need':route._need,
    '_r10_integration_actual_calendars':actual_calendars,
    'ANIMALS':{'COW':None,'SHEEP':None,'GOOSE':None},
    'inventory_total':lambda private,item:private['shed'].get(item,0)+sum(i.get(item,0) for i in private['inventories'])}
exec(compile(ast.Module(body=functions,type_ignores=[]),'isolated_two_guard_helpers','exec'),ns)
contract={'target':[0,0],'stages':[{'op':['BUILD_PASTURE']},{'op':['PLACE','COW',1]}]}
ctx={'unrepresented_commitments':[],'sources':[],'obs':{'private':{'shed':{},'inventories':[{}]}},
    'legacy_workload':{28:7},'legacy_actions':[['WEST']]}
before=deepcopy(ctx)
ns['_r10_integration_note_unrepresented_commitment'](ctx,contract,'COW',(0,0))
contract['stages'][0]['op'][0]='PASS'
try:
    ns['_r10_integration_rows'](ctx)
    rejection=None
except route.BindingError as exc:
    rejection=str(exc)
blocked_actual_calls=len(actual_calls)
clear=deepcopy(before)
clear_result=ns['_r10_integration_rows'](clear)
prototype=ast.parse((HERE/'integration_prototype.py').read_text())
econ=next(n for n in prototype.body if isinstance(n,ast.FunctionDef) and n.name=='economic_plan_prefix')
guards=[]
for node in ast.walk(econ):
    if isinstance(node,ast.If) and ast.dump(node.test,include_attributes=False)==ast.dump(ast.parse('q is None',mode='eval').body,include_attributes=False):
        calls=[n for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_r10_integration_note_unrepresented_commitment']
        guards.extend(calls)
checks={
    'prototype_q_none_branch_calls_guard_once':len(guards)==1,
    'guard_arguments_are_original_contract_item_pos':len(guards)==1 and [ast.unparse(a) for a in guards[0].args]==['_r10_context','contract','item','pos'],
    'helper_retains_target_item_and_reason':ctx['unrepresented_commitments'][0]['target']==[0,0] and ctx['unrepresented_commitments'][0]['item']=='COW' and ctx['unrepresented_commitments'][0]['reason']=='ORIGINAL_COMMITTED_QUOTE_NONE',
    'record_has_independent_original_stage_copy':ctx['unrepresented_commitments'][0]['remaining_stages'][0]['op'][0]=='BUILD_PASTURE',
    'route_rows_reject_before_calendar_work':rejection=='UNREPRESENTED_COMMITMENT_WITHOUT_CALENDAR' and blocked_actual_calls==0,
    'unrelated_original_workload_actions_unchanged':ctx['legacy_workload']==before['legacy_workload'] and ctx['legacy_actions']==before['legacy_actions'],
    'empty_missing_commitments_control_proceeds':clear_result==[] and len(actual_calls)==1,
}
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
report={'checks':checks,'passed':sum(checks.values()),'check_count':len(checks),'all_passed':all(checks.values()),
    'source_sha256':{n:sha(HERE/n) for n in ('integration_prototype.py','integration_helpers.py','test_unrepresented_commitment_guard.py')},
    'counts':{'isolated_helper_definitions_loaded':2,'note_helper_calls':1,'rows_helper_calls':2,
        'candidate_definition_loads':0,'candidate_calls':0,'official_calls':0,'new_complete_matches':0},
    'boundary':'Confirms structural coverage guard; no natural quote(None) trajectory or false admission has been established.'}
path=HERE/('unrepresented_guard_tests_'+stamp+'.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'path':str(path),'checks':len(checks),'passed':sum(checks.values())},ensure_ascii=False))
assert all(checks.values())
