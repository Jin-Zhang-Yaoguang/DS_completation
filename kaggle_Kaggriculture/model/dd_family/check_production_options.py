"""Bounded executor checks using official source observations and rule primitives."""
from pathlib import Path
import copy,json,sys
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'ddbk'))
import action_space as A,rules,task_features as F,production as P
row=next(r for r in json.loads((B/'ddbd/training_manifest.json').read_text())['all_splits'] if r['split']=='train')
rep=json.loads(Path(row['path']).read_text());s=row['seat'];obs=copy.deepcopy(rep['steps'][0][0]['observation']);obs.update(copy.deepcopy(rep['steps'][0][s]['observation']));obs['player']=s;obs['step']=0
farm=A.own_farm(obs);farm['tiles'][0][0]=None;rules._set_farmer_position(farm,0,(0,0));obs['private']['inventories'][0]={};obs['private']['shed']={};obs['private']['seeds']={}
g=(0,0,F.GOAL_INDEX['INSTALL:COW'],1);goals={0:g}
assert P.next_order(obs,0,g)==['BUILD_PASTURE']
assert P.offers(obs,goals)[0][A.MARKET_INDEX['BUY_ANIMAL:COW']]==1
rules._apply_unit_action(farm,obs['private'],0,['BUILD_PASTURE'],10,0,24,100)
obs['private']['shed']['COW']=1
orders=[]
for _ in range(30):
 a=P.next_order(obs,0,g);orders.append(a);rules._apply_unit_action(farm,obs['private'],0,a,10,0,24,100)
 if P.target_done(obs,0,g):break
assert P.target_done(obs,0,g),orders
assert ['PICKUP','COW',1] in orders and orders[-1]==['PLACE','COW',1]
g=(0,0,A.UNIT_INDEX['FEED'],3);obs['private']['shed']['WHEAT']=3;orders=[]
for _ in range(30):
 a=P.next_order(obs,0,g);orders.append(a);rules._apply_unit_action(farm,obs['private'],0,a,10,0,24,100)
 if P.target_done(obs,0,g):break
assert P.target_done(obs,0,g) and ['PICKUP','WHEAT',3] in orders and orders[-1]==['FEED'],orders
assert obs['private']['inventories'][0]['WHEAT']==2
assert not P.requirements(obs,{0:g})[1]
farm['tiles'][1][1]=rules._new_plant('WHEAT',0,24)
c=F.candidates(obs,0,{})
assert not any(tuple(v)==(1,1,A.UNIT_INDEX['PLANT:WHEAT']) for v in c)
farm['tiles'][1][2]=None
c=F.candidates(obs,0,{1:(2,1,F.GOAL_INDEX['INSTALL:COW'],1)})
assert any(tuple(v)==(2,1,A.UNIT_INDEX['CARE']) for v in c)
assert P.valid(obs,0,(2,1,A.UNIT_INDEX['CARE'],1),{1:(2,1,F.GOAL_INDEX['INSTALL:COW'],1)})
x=F.goal_features(obs,0,c,{},{});mx=F.market_features(obs,0,[],{})
schema=json.loads((B/'ddbi/feature_schema.json').read_text());schema.update(revision='production_options_v1',goal_dimensions=x.shape[1],market_dimensions=len(mx),goal_tokens=list(F.GOAL_TOKENS),candidate_token_slice_from_end=[-(F.UT+11),-11],positioned_commitment_dimensions=11)
(B/'ddbk/feature_schema.json').write_text(json.dumps(schema,indent=2)+'\n')
print(json.dumps({'checks':'passed','goal_dimensions':x.shape[1],'market_dimensions':len(mx),'goal_tokens':F.UT}))
