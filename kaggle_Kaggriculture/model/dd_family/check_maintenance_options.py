from pathlib import Path
import copy,json,sys
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'ddbm'))
import action_space as A,rules,task_features as F,maintenance as M,production as P
row=next(r for r in json.loads((B/'ddbd/training_manifest.json').read_text())['all_splits'] if r['split']=='train');r=json.loads(Path(row['path']).read_text());s=row['seat'];o=copy.deepcopy(r['steps'][0][0]['observation']);o.update(copy.deepcopy(r['steps'][0][s]['observation']));o['player']=s;o['step']=0;f=A.own_farm(o)
f['money']=10000;rules._do_hire(f,o['private'],10)
f['tiles'][0][0]=rules._new_animal('COW',0);f['tiles'][0][0]['consecutive_unfed']=1;f['tiles'][1][1]=rules._new_plant('WHEAT',0,24)
rules._set_farmer_position(f,0,(0,0));rules._set_farmer_position(f,1,(1,1));o['private']['inventories'][0]['WHEAT']=1
jobs=M.assign(o,{},set());assert jobs[0][:3]==(0,0,A.UNIT_INDEX['FEED']);assert jobs[1][:3]==(1,1,A.UNIT_INDEX['WATER']);assert len(set(g[:3] for g in jobs.values()))==2
for i,g in jobs.items():rules._apply_unit_action(f,o['private'],i,P.next_order(o,i,g),10,0,24,100)
assert not M.obligations(o)
f['tiles'][0][0]['fed_today']=False;o['private']['inventories'][0]={};o['private']['shed']={};o['step']=23
assert all(g[2]!=A.UNIT_INDEX['FEED'] for g in M.assign(o,{},set()).values())
f['tiles'][1][1]['watered_today']=False;c=M.filter_growth(o,F.candidates(o,1,{}));assert len(c) and all(not F.GOAL_TOKENS[int(g[2])].startswith(('INSTALL:','PLANT:')) for g in c)
print('maintenance checks passed')
