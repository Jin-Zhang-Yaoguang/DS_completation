"""Freeze a train-defined majority-opening subset; reuse identical compiled features read-only."""
from pathlib import Path
import collections,hashlib,json,os,shutil,sys
import numpy as np
B=Path(__file__).resolve().parent;parent=B/'ddbo';child=B/'ddbp';assert not child.exists();child.mkdir();sys.path.insert(0,str(parent));import task_features as F
source=B/'task_policy_data/ddbo';all_rows=json.loads((parent/'source_manifest.json').read_text())['rows'];train_modes=json.loads((B/'diagnostics/ddbo_initial_option_modes.json').read_text())['rows'];counts=collections.Counter(tuple(r['initial_goal']) for r in train_modes);opening=counts.most_common(1)[0][0];selected=[]
for old_index,row in enumerate(all_rows):
 path=source/f'{row["split"]}_{old_index:03}.npz'
 with np.load(path) as z:
  x=z['rank_x'][0];goal=(F.GOAL_TOKENS[int(x[-(F.UT+11):-11].argmax())],int(x[-11]),int(x[-10]))
 if goal==opening:selected.append((old_index,row,path))
assert sum(row['split']=='train' for _,row,_ in selected)==counts[opening]
for p in parent.iterdir():
 if p.suffix=='.py' or p.name=='feature_schema.json':shutil.copy2(p,child/p.name)
config=json.loads((parent/'config.json').read_text());config.update(version='ddbp',method='M&M majority-opening-conditioned production-option distillation',data_selection={'opening':opening,'defined_using':'most frequent exact initial goal in 146 source training episodes; no arena scores','limitation':'Common opening does not prove same teacher executable or identical later strategy'})
(child/'config.json').write_text(json.dumps(config,indent=2)+'\n')
manifest={'source_version':'ddbo','teacher':'M & M & P & Q','rows':[r for _,r,_ in selected],'split_counts':dict(collections.Counter(r['split'] for _,r,_ in selected)),'excluded_test_count':29,'test_replays_opened':False,'selection':config['data_selection']};(child/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
out=B/'task_policy_data/ddbp';out.mkdir();results=[]
for index,(old_index,row,path) in enumerate(selected):
 target=out/f'{row["split"]}_{index:03}.npz';os.link(path,target)
 audit=json.loads(path.with_suffix('.json').read_text());assert hashlib.sha256(path.read_bytes()).hexdigest()==audit['sha256'];audit.update(index=index,parent_version='ddbo',parent_index=old_index)
 target.with_suffix('.json').write_text(json.dumps(audit,indent=2)+'\n');results.append(audit)
for name in ['task_features.py','action_space.py','rules.py','features.py']:assert (parent/name).read_bytes()==(child/name).read_bytes()
plan={'version':'ddbp','rows':manifest['rows'],'test_opened':False,'selection':config['data_selection'],'parent_plan_sha256':hashlib.sha256((source/'plan.json').read_bytes()).hexdigest(),'readonly_hardlinked_npz':True,'hashes':{str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),*child.glob('*.py'),child/'config.json',child/'source_manifest.json']}}
(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');(out/'manifest.json').write_text(json.dumps({'expected':len(results),'completed':len(results),'rows':results,'source_exact_states':all(r['source_exact_719_states'] for r in results),'derived_from_identical_features':True},indent=2)+'\n')
p=B/'registry.json';reg=json.loads(p.read_text());reg['versions'].append({'version':'ddbp','index':67,'parent':'ddbo','status':'DATA_READY','method':config['method'],'hypothesis':'Reduce conflicting teacher choices by fixing the most frequent source-training opening; do not infer common executable from the opening alone.'});reg['next_version']=None;p.write_text(json.dumps(reg,indent=2)+'\n');print(json.dumps({'opening':opening,'split_counts':manifest['split_counts'],'identical_features':True,'test_used':False}))
