#!/usr/bin/env python3
"""R8选择目标隔离微测，人工局部状态，无完整新比赛。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import ast,hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'r4_contract_design'))
import test_microcases as common
engine=common.scaffold.engine
checks={};details={};runs=[]
def load(parent=False):
    path=HERE/('parent_r7.py'if parent else'main.py');sp=importlib.util.spec_from_file_location('r8_test_'+str(parent),path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

def clean(seat=0,day=0,hour=0,cash=3000,sites=None):
    e=common.empty_env(seat,day,hour);f=e.state[0].observation.farms[seat]
    f['farmer']=[4,4];f['money']=cash;f['unlocked_quadrants']=['NW']
    f['tiles']=[[None if x<5 and y<5 and(sites is None or(x,y)in sites)else'LOCKED'for x in range(10)]for y in range(10)]
    for s in e.state:s.observation.town['unlocked_shops']=[]
    return e

def controlled(mode,cash=3000,hour=0,sites={(4,4)}):
    m=load();m.PARAMS['investment_selection']=mode;e=clean(cash=cash,hour=hour,sites=sites);o=engine.observed(e,0)
    def quote(obs,item,pos,model,seed_credit=False,already_owned=False,committed=False):
        if item not in('MELON','SHEEP'):return None
        net,work=(100.,10)if item=='MELON'else(120.,20)
        fixed=80 if item=='MELON'else 500
        buffer=m.feed_ledger(obs,model,{obs['day']:3},0)['opportunity']if item=='SHEEP'else 0
        gross=net+fixed+buffer
        return {'item':item,'position':pos,'build_first':item=='SHEEP','start_step_model':obs['step']+3,'first_product_day':6,
                'calendar':{'goods':{},'work':{obs['day']:work},'feed':{}},'fixed_cash':fixed,'gross_cash_model':gross,
                'feed_cost_model':0,'net_before_hiring_model':net,'labor':work,'score_before_hiring':net/work,'setup_work':{obs['day']:1}}
    m.investment_quote=quote;st=m.new_state(o);p=m.economic_plan(o,st);return m,o,st,p

for mode,expected in [('labor_ratio','MELON'),('terminal_net','SHEEP')]:
    m,o,st,p=controlled(mode);q=p['admitted_investments'][0]
    checks[mode+'_same_quotes_different_choice']=q['item']==expected
    checks[mode+'_execution_score_stays_ratio']=q['score']==q['net_cash_model']/q['labor']
    checks[mode+'_selection_semantics']=q['selection_score']==(q['net_cash_model']if mode=='terminal_net'else q['score'])
    details[mode]={'expert':st['expert'],'item':q['item'],'net':q['net_cash_model'],'work':q['labor'],'score':q['score'],'selection_score':q['selection_score']}

m,o,st,p=controlled('terminal_net',cash=80)
checks['high_net_cash_infeasible_rejected']=all(q['item']!='SHEEP'for q in p['admitted_investments'])and p['rejected_types'].get('cash',0)>0 and p['admitted_investments'][0]['item']=='MELON'
m,o,st,p=controlled('terminal_net',cash=3000,hour=8)
checks['high_net_labor_infeasible_rejected']=all(q['item']!='SHEEP'for q in p['admitted_investments'])and p['rejected_types'].get('labor',0)>0
m,o,st,p=controlled('terminal_net',cash=10000,sites={(4,4),(3,4),(4,3)})
checks['one_new_animal_per_frame']=sum(q['item']in m.ANIMALS for q in p['admitted_investments'])==1

# 相同plan和作物执行分的任务价值完全一致；选择分不泄漏到make_tasks。
e=clean(day=0,hour=0,cash=3000);e.state[0].observation.private['seeds']={'MELON':2}
old,new=load(True),load();o=engine.observed(e,0);st=old.new_state(o);plan=old.economic_plan(o,st)
a=old.make_tasks(deepcopy(o),deepcopy(st),deepcopy(plan));b=new.make_tasks(deepcopy(o),deepcopy(st),deepcopy(plan))
checks['same_plan_execution_tasks_equal']=a==b
checks['same_plan_crop_task_value_equal']=bool(a)and [t['value']for t in a]==[t['value']for t in b]

# 默认net仍使用预算后score作为执行分，日志分开三个语义。
for seat in [0,1]:
    e=clean(seat,cash=6000,sites={(4,4),(3,4),(4,3)})
    m=load();o=engine.observed(e,seat);st=m.new_state(o);p=m.economic_plan(o,st)
    qs=p['admitted_investments'];checks['real_net_one_animal_s'+str(seat)]=sum(q['item']in m.ANIMALS for q in qs)<=1
    checks['real_net_scores_s'+str(seat)]=all(q['selection_score']==q['net_cash_model']and q['score']==q['net_cash_model']/max(1,q['labor'])for q in qs)
    m._STATES[seat]=st;m.market_orders(o,st,p,m.make_tasks(o,st,p),[['PASS']]);payload=m.diagnostics();json.dumps(payload,allow_nan=False)
    checks['three_score_fields_logged_s'+str(seat)]=bool(qs)and all(all(k in q for k in ['net_cash_model','score','selection_score'])for q in payload[str(seat)]['investment_receipts'][-1]['admitted'])

for seat in[0,1]:
    for case,d,h,n in [('initial_investment',0,0,12),('existing_care_crossday',10,16,8),('in_transit',3,3,10)]:
        outcomes=[]
        for parent in[True,False]:
            e=clean(seat,day=d,hour=h,cash=6000)
            if case=='existing_care_crossday':
                e.state[0].observation.farms[seat]['tiles'][4][4]=engine.RULES._new_animal('COW',0)
                e.state[0].observation.farms[seat]['tiles'][4][3]=engine.RULES._new_plant('STRAWBERRY',0,240)
                e.state[seat].observation.private['shed']={'WHEAT':8,'FERTILIZER':3};e.state[seat].observation.private['seeds']={'CARROT':2}
            if case=='in_transit':e.state[seat].observation.private['shed']={'SHEEP':1,'WHEAT':10}
            m=load(parent)
            if not parent:m.PARAMS['investment_selection']='labor_ratio'
            result,m=common.run(e,seat,n,case+('_R7'if parent else'_R8_ratio'),module=m)
            runs.append(result);outcomes.append(result)
        ra,rb=outcomes
        checks[case+'_ratio_actions_equal_s'+str(seat)]=[r['applied']for r in ra['rows']]==[r['applied']for r in rb['rows']]
        checks[case+'_ratio_terminal_equal_s'+str(seat)]=ra['final']==rb['final']

# 错误配置不能默默落回另一套目标。
m=load();m.PARAMS['investment_selection']='unknown';o=engine.observed(clean(),0)
try:m.economic_plan(o,m.new_state(o));checks['unknown_selection_mode_rejected']=False
except ValueError:checks['unknown_selection_mode_rejected']=True
old=ast.parse((HERE/'parent_r7.py').read_text());new=ast.parse((HERE/'main.py').read_text())
of={n.name:ast.dump(n,include_attributes=False)for n in old.body if isinstance(n,ast.FunctionDef)};nf={n.name:ast.dump(n,include_attributes=False)for n in new.body if isinstance(n,ast.FunctionDef)}
changed=[k for k in of if of[k]!=nf[k]];checks['only_economic_plan_changed']=changed==['economic_plan']
sha=hashlib.sha256((HERE/'main.py').read_bytes()).hexdigest()
result={'source_sha256':sha,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks':checks,'passed':sum(checks.values()),'total':len(checks),'details':details,'changed_functions':changed,'runs':runs,'complete_matches':0,'new_replays_opened':False}
path=HERE/('micro_'+sha[:12]+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json');path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
print(json.dumps({'result':str(path),'passed':sum(checks.values()),'total':len(checks),'failed':[k for k,v in checks.items()if not v]},ensure_ascii=False))
