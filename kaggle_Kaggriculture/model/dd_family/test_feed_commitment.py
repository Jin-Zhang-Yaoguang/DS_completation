"""Functional regression for the unplaced-animal purchase/pickup deadlock."""
from pathlib import Path
import copy,contextlib,io,json,sys
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'ddl'))
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    from kaggle_environments import make
import main
env=make('kaggriculture',configuration={'seed':919260010},debug=False);env.reset(2)
obs=copy.deepcopy(env.state[0].observation);obs['step']=0
policy=main.Agent();policy.day=0;policy.goal=[None]*100;policy.hands=0;policy.land=1
obs['private']['shed']['COW']=1;obs['private']['shed']['WHEAT']=1
action=policy.market(copy.deepcopy(obs))
assert not any(o[0]=='SELL' and o[1]=='WHEAT' for o in action),action
obs['private']['shed']['WHEAT']=0
action=policy.market(copy.deepcopy(obs))
assert ['BUY_PRODUCT','WHEAT',1] in action,action
obs['private']['shed']['COW']=0;obs['private']['inventories'][0]={'COW':1}
action=policy.market(copy.deepcopy(obs))
assert ['BUY_PRODUCT','WHEAT',1] in action,action
print(json.dumps({'unplaced_shed_animal_feed':'PASS','carried_animal_feed':'PASS','reserved_food_not_sold':'PASS'}))
