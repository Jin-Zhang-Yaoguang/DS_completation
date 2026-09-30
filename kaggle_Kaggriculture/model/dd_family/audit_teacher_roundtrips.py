"""Measure source fills and cancel matched within-turn trades in fixed-action replays.

Counterfactuals are diagnostics with recorded opponents, not dynamic arena wins.
"""
from pathlib import Path
import collections,concurrent.futures,contextlib,copy,hashlib,importlib,io,json,sys
import numpy as np
B=Path(__file__).resolve().parent;OUT=B/'teacher_market_audit'

def run(k):
    sys.path.insert(0,str(B/'ddbh'));import action_space as A
    row=json.loads((B/'ddbd/training_manifest.json').read_text())['episodes'][k];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat']
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    cfg=dict(rep['configuration']);cfg['seed']=rep['info']['seed'];now=[0];tokens=np.zeros((719,10),np.int16);quantities=np.zeros((719,10),np.int16);cash=np.zeros((719,10),np.float64)
    originals={n:getattr(eng,n) for n in ['_commit_unit','_do_hire','_do_buy_land']}
    def commit(op,item,price,farm,private,market,capacity=100):
        frame=sys._getframe(1);slot=frame.f_locals['i'];player=frame.f_locals['player_id'];result=originals['_commit_unit'](op,item,price,farm,private,market,capacity)
        if result and player==seat:tokens[now[0],slot]=A.MARKET_INDEX[op+':'+item];quantities[now[0],slot]+=1;cash[now[0],slot]+=price*(1 if op=='SELL' else -1)
        return result
    def hire(farm,private,*args,**kwargs):
        frame=sys._getframe(1);slot=frame.f_locals['i'];player=frame.f_locals['player_id'];before=farm['money'];n=len(farm['hands']);result=originals['_do_hire'](farm,private,*args,**kwargs)
        if player==seat and len(farm['hands'])>n:tokens[now[0],slot]=A.MARKET_INDEX['HIRE'];quantities[now[0],slot]=1;cash[now[0],slot]=farm['money']-before
        return result
    def land(farm,*args,**kwargs):
        frame=sys._getframe(1);slot=frame.f_locals['i'];player=frame.f_locals['player_id'];before=farm['money'];n=len(farm['unlocked_quadrants']);result=originals['_do_buy_land'](farm,*args,**kwargs)
        if player==seat and len(farm['unlocked_quadrants'])>n:tokens[now[0],slot]=A.MARKET_INDEX['BUY_LAND'];quantities[now[0],slot]=1;cash[now[0],slot]=farm['money']-before
        return result
    env=make('kaggriculture',configuration=cfg);env.reset(2)
    for n,fn in {'_commit_unit':commit,'_do_hire':hire,'_do_buy_land':land}.items():setattr(eng,n,fn)
    try:
        for t in range(719):now[0]=t;env.step([copy.deepcopy(s['action']) for s in rep['steps'][t+1]])
    finally:
        for n,fn in originals.items():setattr(eng,n,fn)
    assert [float(s.reward) for s in env.state]==rep['rewards'];assert 3000+cash.sum()==rep['rewards'][seat]
    net=quantities.copy();matched=collections.Counter();spread_cash=collections.Counter();roundturns=collections.Counter()
    for t in range(719):
        for item in ['WHEAT','FERTILIZER']:
            buy=np.flatnonzero(tokens[t]==A.MARKET_INDEX['BUY_PRODUCT:'+item]);sell=np.flatnonzero(tokens[t]==A.MARKET_INDEX['SELL:'+item]);n=min(int(quantities[t,buy].sum()),int(quantities[t,sell].sum()))
            if not n:continue
            matched[item]+=n;roundturns[item]+=1
            spread_cash[item]+=n*(cash[t,sell].sum()/quantities[t,sell].sum()+cash[t,buy].sum()/quantities[t,buy].sum())
            for slots in [buy,sell]:
                left=n
                for slot in slots:
                    take=min(left,int(net[t,slot]));net[t,slot]-=take;left-=take
                assert left==0
    outcomes={}
    for name,qty in [('canonical_fills',quantities),('cancel_matched',net)]:
        env=make('kaggriculture',configuration=cfg);env.reset(2)
        for t in range(719):
            actions=[copy.deepcopy(s['action']) for s in rep['steps'][t+1]];market=[];last=max(np.flatnonzero(tokens[t]).tolist(),default=-1)
            for slot in range(last+1):
                tok=int(tokens[t,slot]);q=int(qty[t,slot])
                if not tok or not q:order=['BUY_SEED','WHEAT',0]
                else:
                    order=A.MARKET_TOKENS[tok].split(':')
                    if len(order)==2:order.append(q)
                market.append(order)
            actions[seat]['market']=market;env.step(actions)
            if name=='canonical_fills':
                obs=dict(rep['steps'][t+1][0]['observation']);obs.update(rep['steps'][t+1][seat]['observation'])
                for field in ['farms','private','market','town']:assert env.state[seat].observation[field]==obs[field],(k,t,field)
        outcomes[name]=[float(s.reward) for s in env.state]
    result={'prototype':k,'source_sha256':row['sha256'],'seed':row['seed'],'seat':seat,'source_rewards':rep['rewards'],'canonical_all_719_states_exact':True,'cash_conserved':True,'matched_roundtrip_units':dict(matched),'turns_with_roundtrip':dict(roundturns),'average_price_matched_spread_attribution':dict(spread_cash),'counterfactual_rewards':outcomes['cancel_matched'],'own_cash_delta':outcomes['cancel_matched'][seat]-rep['rewards'][seat],'opponent_cash_delta':outcomes['cancel_matched'][1-seat]-rep['rewards'][1-seat],'scope':'Recorded both-side unit actions and recorded opponent market; not dynamic games. Matched spread is an accounting allocation, not causal profit.'}
    np.savez_compressed(OUT/f'{k:03}_fills.npz',tokens=tokens,quantities=quantities,cash=cash,net_quantities=net)
    (OUT/f'{k:03}_audit.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    OUT.mkdir(exist_ok=True);indices=list(range(21));assert not (OUT/'summary.json').exists()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        rows=[]
        for r in pool.map(run,indices):rows.append(r);print(r['prototype'],r['own_cash_delta'],r['matched_roundtrip_units'],flush=True)
    summary={'source':'Boey train only','episodes':21,'rows':rows,'mean_own_cash_delta':float(np.mean([r['own_cash_delta'] for r in rows])),'median_own_cash_delta':float(np.median([r['own_cash_delta'] for r in rows])),'mean_opponent_cash_delta':float(np.mean([r['opponent_cash_delta'] for r in rows])),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print({k:v for k,v in summary.items() if k!='rows'},flush=True)
