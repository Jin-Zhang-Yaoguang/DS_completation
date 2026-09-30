"""只用真实 Kaggle raw loader 加载定义并检查入口，不调用 agent。"""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
from kaggle_environments.agent import get_last_callable
HERE=Path(__file__).resolve().parent
path=HERE/'integration_prototype.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=path.read_text();before=sha(path)
entry=get_last_callable(source,path=str(path))
checks={
 'real_loader_name_agent':entry.__name__=='agent',
 'real_loader_same_env_agent':entry is entry.__globals__['agent'],
 'empty_state_no_agent_calls':entry.__globals__['_STATES']=={},
 'route_default_matches':entry.__globals__['PARAMS']['r10_route_mode']=='future_failure_certificate',
 'legacy_static_function_exists':callable(entry.__globals__['_r10_integration_legacy_economic_plan_prefix']),
 'unchanged_parent_product_order':entry.__globals__['PRODUCTS']==('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER'),
 'unchanged_parent_animal_mapping_type':isinstance(entry.__globals__['ANIMALS'],dict),
 'last_inserted_callable_agent':[k for k,v in entry.__globals__.items() if callable(v)][-1]=='agent',
 'source_unchanged':sha(path)==before,
}
loader_source=Path(__import__('kaggle_environments.agent',fromlist=['x']).__file__)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
report={'checks':checks,'passed':sum(checks.values()),'check_count':len(checks),'all_passed':all(checks.values()),
    'prototype_sha256':before,'loader_source':str(loader_source),'loader_sha256':sha(loader_source),
    'harness_sha256':sha(Path(__file__)),'counts':{'prototype_definition_loads':1,'candidate_calls':0,'official_interpreter_steps':0,'new_complete_matches':0}}
output=HERE/('prototype_entry_'+stamp+'.json');output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'path':str(output),'checks':len(checks),'passed':sum(checks.values()),'sha256':before},ensure_ascii=False))
assert all(checks.values())
