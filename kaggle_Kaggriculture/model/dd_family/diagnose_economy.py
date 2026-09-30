"""Instrument official settlement without changing actions or accounting."""
from pathlib import Path
import argparse,collections,concurrent.futures,contextlib,copy,gzip,importlib,io,json,sys
B=Path(__file__).resolve().parent

def run(task):
    version,seed,op=task
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    engine=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    sys.path.insert(0,str(B/version));import main as policy,action_space as space,rules
    agent=policy.Agent();proto=json.loads((B/'protocol.json').read_text());opp=next(r for r in proto['opponents'] if r['name']==op)
    other=get_last_callable((B/opp['file']).read_text(),path=str(B/opp['file']))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2)
    trades=collections.defaultdict(lambda:[0,0]);atomic=collections.defaultdict(int);spills=collections.Counter();invalid=[];current=[0];identity={};pid={}
    originals={n:getattr(engine,n) for n in ['_process_market','_commit_unit','_do_hire','_do_buy_land','_drop_inventories_to_shed','_end_of_day']}
    def market(state,env):
        identity.clear();identity.update({id(f):i for i,f in enumerate(state[0].observation.farms)})
        return originals['_process_market'](state,env)
    def commit(op,item,price,farm,private,market,shed_capacity=100):
        ok=originals['_commit_unit'](op,item,price,farm,private,market,shed_capacity)
        if ok:
            key=(identity[id(farm)],current[0]//24,op,item);trades[key][0]+=1;trades[key][1]+=price
        return ok
    def hire(farm,*args,**kwargs):
        before=farm['money'];r=originals['_do_hire'](farm,*args,**kwargs);atomic[(identity[id(farm)],'HIRE')]+=before-farm['money'];return r
    def land(farm,*args,**kwargs):
        before=farm['money'];r=originals['_do_buy_land'](farm,*args,**kwargs);atomic[(identity[id(farm)],'LAND')]+=before-farm['money'];return r
    def end(state,env,day):
        pid.clear();pid.update({id(s.observation.private):i for i,s in enumerate(state)})
        return originals['_end_of_day'](state,env,day)
    def drop(private,capacity):
        before=collections.Counter(private['shed'])
        for inv in private['inventories']:before.update(inv)
        r=originals['_drop_inventories_to_shed'](private,capacity)
        for item,n in (before-collections.Counter(private['shed'])).items():spills[(pid[id(private)],current[0]//24,item)]+=n
        return r
    patches={'_process_market':market,'_commit_unit':commit,'_do_hire':hire,'_do_buy_land':land,'_drop_inventories_to_shed':drop,'_end_of_day':end}
    for n,f in patches.items():setattr(engine,n,f)
    initial=[s.observation.farms[i]['money'] for i,s in enumerate(env.state)]
    try:
        for t in range(719):
            current[0]=t;obs=[copy.deepcopy(s.observation) for s in env.state]
            for o in obs:o['step']=t
            action=agent.act(obs[0]);k=agent.config['fixed_prototype'];shadow=copy.deepcopy(obs[0])
            for i,order in enumerate([action['farmer']]+action['hands']):
                tok=int(agent.arr['unit_tokens'][t,k,i]);name=space.UNIT_TOKENS[tok]
                if not space.unit_legal_mask(shadow,i)[tok]:
                    x,y=space.unit_position(shadow,i);expected=list(map(lambda n:round(float(n)*9),agent.arr['units'][t,k,i,2:4]))
                    invalid.append({'step':t,'unit':i,'requested':name,'actual':order,'position':[x,y],'reference_position':expected,'tile':copy.deepcopy(shadow['farms'][0]['tiles'][y][x]),'inventory':dict(space.unit_inventory(shadow,i)),'shed':dict(shadow['private']['shed'])})
                rules._apply_unit_action(shadow['farms'][0],shadow['private'],i,order,10,t//24,24,100)
            env.step([action,other(obs[1])])
    finally:
        for n,f in originals.items():setattr(engine,n,f)
    rewards=[float(s.reward) for s in env.state]
    tx=[{'seat':k[0],'day':k[1],'op':k[2],'item':k[3],'qty':v[0],'cash':v[1]} for k,v in sorted(trades.items())]
    totals={}
    for seat in [0,1]:
        byitem={item:{'qty':sum(r['qty'] for r in tx if r['seat']==seat and r['op']=='SELL' and r['item']==item),'cash':sum(r['cash'] for r in tx if r['seat']==seat and r['op']=='SELL' and r['item']==item)} for item in space.PRODUCTS}
        sales=sum(r['cash'] for r in tx if r['seat']==seat and r['op']=='SELL');purchases=sum(r['cash'] for r in tx if r['seat']==seat and r['op']!='SELL');wages=atomic[seat,'HIRE'];landcost=atomic[seat,'LAND']
        assert initial[seat]+sales-purchases-wages-landcost==rewards[seat]
        totals[seat]={'sales':byitem,'sales_cash':sales,'purchases':purchases,'wages':wages,'land':landcost,'cash_reconciled':True}
    out={'version':version,'seed':seed,'opponent':op,'rewards':rewards,'margin':rewards[0]-rewards[1],'totals':totals,'transactions':tx,'invalid_units':invalid,'invalid_counts':dict(collections.Counter(r['requested'] for r in invalid)),'position_mismatch':sum(r['position']!=r['reference_position'] for r in invalid),'spills':[{'seat':k[0],'day':k[1],'item':k[2],'qty':v} for k,v in spills.items()]}
    for p in (B/version/'runs').glob(f'*/games/{op}_{seed}_0.json.gz'):
        old=json.load(gzip.open(p,'rt'));assert old['own_cash']==rewards[0] and old['opponent_cash']==rewards[1],p
    directory=B/'economic_audit'/version;directory.mkdir(parents=True,exist_ok=True)
    with gzip.open(directory/f'{op}_{seed}.json.gz','wt') as f:json.dump(out,f,separators=(',',':'))
    return {k:v for k,v in out.items() if k not in ['transactions','invalid_units','spills']}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('version');ap.add_argument('--seeds',nargs='+',type=int,required=True);ap.add_argument('--opponent',default='y68v');ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        for r in pool.map(run,[(a.version,s,a.opponent) for s in a.seeds]):print(json.dumps(r),flush=True)
