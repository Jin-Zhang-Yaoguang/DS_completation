"""Replay recorded development actions to attribute real execution and cash flows."""
from pathlib import Path
import collections,concurrent.futures,contextlib,copy,gzip,importlib,io,json,sys
B=Path(__file__).resolve().parent

def run(task):
    version,seed=task;seat=0
    with gzip.open(B/version/'runs/development01/games'/f'y68v_{seed}_{seat}.json.gz','rt') as f:saved=json.load(f)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
        eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    sys.path.insert(0,str(B/'ddbg'));import rules,action_space as A
    protocol=json.loads((B/'protocol.json').read_text());op=next(x for x in protocol['opponents'] if x['name']=='y68v');opponent=get_last_callable((B/op['file']).read_text(),path=str(B/op['file']))
    env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);cashflows=collections.Counter();fills=collections.Counter();daily=[];services=collections.Counter()
    original={n:getattr(eng,n) for n in ['_commit_unit','_do_hire','_do_buy_land']}
    def commit(op,item,price,farm,private,market,capacity=100):
        player=sys._getframe(1).f_locals['player_id'];r=original['_commit_unit'](op,item,price,farm,private,market,capacity)
        if r and player==seat:cashflows[op+':'+item]+=price if op=='SELL' else -price;fills[op+':'+item]+=1
        return r
    def hire(farm,private,*args,**kwargs):
        player=sys._getframe(1).f_locals['player_id'];before=farm['money'];r=original['_do_hire'](farm,private,*args,**kwargs)
        if player==seat:cashflows['HIRE']+=farm['money']-before
        return r
    def land(farm,*args,**kwargs):
        player=sys._getframe(1).f_locals['player_id'];before=farm['money'];r=original['_do_buy_land'](farm,*args,**kwargs)
        if player==seat:cashflows['BUY_LAND']+=farm['money']-before
        return r
    for n,fn in {'_commit_unit':commit,'_do_hire':hire,'_do_buy_land':land}.items():setattr(eng,n,fn)
    try:
        for t in range(719):
            obs=copy.deepcopy(env.state[seat].observation);obs['step']=t;own=saved['trace'][t]['action'];farm=obs['farms'][seat];priv=obs['private']
            units=[own['farmer'],*own['hands']]
            for i,a in enumerate(units):
                before=copy.deepcopy((farm['tiles'],priv['inventories'][i],priv['shed'],priv['seeds']))
                rules._apply_unit_action(farm,priv,i,a,10,t//24,24,100)
                if a[0] not in ['PASS',*A.MOVES] and before!=(farm['tiles'],priv['inventories'][i],priv['shed'],priv['seeds']):services[a[0]]+=1
            other=copy.deepcopy(env.state[1-seat].observation);other['step']=t;env.step([own,opponent(other)])
            now=env.state[seat].observation;assert float(now.farms[seat]['money'])==saved['trace'][t]['cash'],(version,seed,t,'cash divergence')
            if t%24==23:
                tiles=[v for row in farm['tiles'] for v in row if isinstance(v,dict)];animals=[v for v in tiles if v.get('animal')];plants=[v for v in tiles if v.get('crop')]
                escaped=0;dead_plants=0
                for y in range(10):
                    for x in range(10):
                        before=farm['tiles'][y][x];after=now.farms[seat]['tiles'][y][x]
                        if isinstance(before,dict) and before.get('animal') and not (isinstance(after,dict) and after.get('animal')):escaped+=1
                        if isinstance(before,dict) and before.get('crop') and not (isinstance(after,dict) and after.get('crop')):dead_plants+=1
                daily.append({'day':t//24,'animals':len(animals),'unfed_at_close':sum(not a['fed_today'] for a in animals),'uncared_at_close':sum(not a['cared_today'] for a in animals),'escaped':escaped,'plants':len(plants),'unwatered_at_close':sum(not p['watered_today'] for p in plants),'plants_disappeared_at_close':dead_plants,'held_yield_units':sum(v.get('yield_units',0) for v in tiles)})
    finally:
        for n,fn in original.items():setattr(eng,n,fn)
    rewards=[float(s.reward) for s in env.state];assert rewards==[saved['own_cash'],saved['opponent_cash']]
    assert 3000+sum(cashflows.values())==rewards[0]
    result={'version':version,'seed':seed,'seat':seat,'exact_saved_719_cash_states_and_final_both_rewards':True,'cash_conserved':True,'rewards':rewards,'cashflows':dict(cashflows),'fills':dict(fills),'successful_services':dict(services),'daily':daily,'escaped':sum(d['escaped'] for d in daily),'unfed_animal_days':sum(d['unfed_at_close'] for d in daily),'unwatered_plant_days':sum(d['unwatered_at_close'] for d in daily)}
    (B/'diagnostics'/f'{version}_{seed}_execution.json').write_text(json.dumps(result,indent=2)+'\n')
    return {k:v for k,v in result.items() if k not in ['cashflows','fills','successful_services','daily']}

if __name__=='__main__':
    versions=sys.argv[1:] or ['ddbh']
    tasks=[(v,s) for v in versions for s in range(919260010,919260014)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(run,tasks))
    (B/'diagnostics'/('task_execution_'+'_'.join(versions)+'_manifest.json')).write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
