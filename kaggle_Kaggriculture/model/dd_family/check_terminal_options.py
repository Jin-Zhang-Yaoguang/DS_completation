"""Terminal option feasibility, deposit deadline, and independent capital mask."""
from pathlib import Path
import collections,copy,json,sys
import numpy as np
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'ddbo'))
import action_space as A,rules,task_features as F,maintenance as M,production as P
from main import Agent
r=json.loads((B/'ddbo/source_manifest.json').read_text())['rows'][0];rep=json.loads(Path(r['path']).read_text());s=r['seat'];o=copy.deepcopy(rep['steps'][0][0]['observation']);o.update(copy.deepcopy(rep['steps'][0][s]['observation']));o['player']=s;o['step']=696;farm=A.own_farm(o)
c=F.candidates(o,0,{});kept=M.terminal_reachable(o,0,M.filter_growth(o,c));assert len(kept) and int(kept[0][2])==0
assert all(F.GOAL_TOKENS[int(g[2])] in ['PASS','DROP','HARVEST','COLLECT_FERTILIZER'] or F.GOAL_TOKENS[int(g[2])].startswith('PLACE:') and F.GOAL_TOKENS[int(g[2])].split(':')[1] in A.PRODUCTS for g in kept)
rules._set_farmer_position(farm,0,(4,4));candidate=np.asarray([(4,4,0),(4,3,A.UNIT_INDEX['HARVEST'])],np.int16)
o['step']=715;assert len(M.terminal_reachable(o,0,candidate))==2
o['step']=716;assert len(M.terminal_reachable(o,0,candidate))==1
rules._set_farmer_position(farm,0,(0,0));o['private']['inventories'][0]={'MILK':1};o['private']['shed']={};home=P.home((0,0));o['step']=719-(M.distance((0,0),home)+1)
while o['step']<=718:
 g=M.terminal_return(o,0);assert g
 a=P.next_order(o,0,g);rules._apply_unit_action(farm,o['private'],0,a,10,29,24,100);o['step']+=1
assert o['private']['shed']['MILK']==1 and not o['private']['inventories'][0]
class Rank:
 def predict(self,x):return np.zeros(len(x))
class Quantity:
 def predict(self,x):return np.ones(len(x))
class Market:
 a={'classes':np.arange(F.MT)}
 def predict(self,x):
  v=np.zeros((len(x),F.MT));v[:,0]=1;v[:,A.MARKET_INDEX['BUY_LAND']]=100;v[:,A.MARKET_INDEX['BUY_ANIMAL:COW']]=99;return v
agent=Agent.__new__(Agent);agent.rank=Rank();agent.quantity=Quantity();agent.market=Market();agent.marketq=Quantity();agent.goals={};agent.previous={};agent.forced=set();agent.day=-1;agent.stats=collections.Counter();agent.last={};o['step']=696
assert agent.act(o)['market']==[]
print('terminal candidate, return deadline, and independent market-mask checks passed')
