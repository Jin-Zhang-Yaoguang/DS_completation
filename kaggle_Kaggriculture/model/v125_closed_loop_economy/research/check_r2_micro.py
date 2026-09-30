"""用已经公开的短场景检查R2，保留原R0对照；不生成完整新比赛。"""
import importlib.util,json,sys,hashlib
from pathlib import Path
from copy import deepcopy
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'research/procurement_audit'))
import run_dependency_microcases as cases
import run_microcases as engine
rows=[]
for seat in (0,1):
 for scenario in ('remote_fertilizer_blocks_crop','no_fertilizer_control','fertilizer_at_crop_control'):
  outcomes={}
  for candidate in ('V125-R0','V125-R2'):
   path=BASE/'candidates'/candidate/'main.py'
   spec=importlib.util.spec_from_file_location('isolated_'+candidate,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
   env=cases.setup(seat,scenario);steps=[]
   for _ in range(6):
    obs=engine.observed(env,seat);action=mod.agent(obs);pair=[deepcopy(engine.PASS),deepcopy(engine.PASS)];pair[seat]=action
    engine.official_step(env,pair);steps.append(action)
   final=cases.compact(engine.observed(env,seat),seat)
   outcomes[candidate]={'actions':steps,'final':final,'candidate_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  rows.append({'seat':seat,'scenario':scenario,**outcomes})
checks={}
for row in rows:
 key=str(row['seat'])+'_'+row['scenario'];a,b=row['V125-R0'],row['V125-R2']
 checks[key+'_survives']=b['final']['crop']['kind']=='PLANT'
 checks[key+'_harvested']=b['final']['shed'].get('STRAWBERRY',0)>=1
 if row['scenario']=='fertilizer_at_crop_control':checks[key+'_control_unchanged']=a['actions']==b['actions']
result={'candidate':'V125-R2','role':'MICRO_NOT_STRENGTH','checks':checks,'pass':all(checks.values()),'runs':rows}
(BASE/'research/r2_micro_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pass':result['pass'],'checks':checks},ensure_ascii=False))
assert result['pass']
