"""Attribute PASS to active commitments and visible service opportunities."""
from pathlib import Path
import collections,concurrent.futures,contextlib,copy,gzip,hashlib,importlib,io,json,sys
B=Path(__file__).resolve().parent
def run(task):
    version,seed=task;sys.path.insert(0,str(B/version));import action_space as A,rules
    with gzip.open(B/version/'runs/development01/games'/f'y68v_{seed}_0.json.gz','rt') as f:saved=json.load(f)
    has_goals=all('goals' in r['diagnostic'] for r in saved['trace'])
    if not has_goals:
        assert version=='ddbj','Legacy inference audited only for ddbj main.py'
        actual_pass=sum(a[0]=='PASS' for r in saved['trace'] for a in [r['action']['farmer'],*r['action']['hands']])
        # In ddbj, wait_actions increments exactly when the chosen goal token is 0.
        assert actual_pass==saved['stats']['wait_actions']
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
        eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    op=next(r for r in json.loads((B/'protocol.json').read_text())['opponents'] if r['name']=='y68v');path=B/op['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2);counts=collections.Counter();samples=[];now=[0];original=eng._apply_unit_action
    def apply(farm,private,i,action,*args,**kwargs):
        player=sys._getframe(1).f_locals['i'];t=now[0]
        if player==0 and action[0]=='PASS':
            counts['pass']+=1;goal=saved['trace'][t]['diagnostic'].get('goals',{}).get(str(i));counts['committed_pass' if goal else 'uncommitted_pass']+=1
            if not goal and t//24<29:
                pos=eng._farmer_position(farm,i);bag=private['inventories'][i];remaining=min(24-t%24,719-t);near=collections.Counter()
                for y,row in enumerate(farm['tiles']):
                    for x,tile in enumerate(row):
                        if not isinstance(tile,dict):continue
                        distance=abs(x-pos[0])+abs(y-pos[1]);cost=distance+1
                        if cost>remaining:continue
                        if tile.get('animal'):
                            if not tile.get('cared_today'):near['CARE']+=1
                            if not tile.get('fed_today'):
                                home=min(sorted(A.SHED_ACCESS),key=lambda xy:abs(xy[0]-pos[0])+abs(xy[1]-pos[1]));fetch=0 if bag.get('WHEAT',0)>0 else abs(pos[0]-home[0])+abs(pos[1]-home[1])+1+abs(x-home[0])+abs(y-home[1])+1
                                if bag.get('WHEAT',0)>0 or private['shed'].get('WHEAT',0)>0 and fetch<=remaining:near['FEED']+=1
                            if tile.get('yield_units',0)>0:near['HARVEST']+=1
                            if tile.get('fertilizer_available'):near['COLLECT_FERTILIZER']+=1
                        elif tile.get('crop'):
                            if not tile.get('watered_today'):near['WATER']+=1
                            if tile.get('yield_units',0)>0 and t//24>=tile['planted_day']+eng.CROPS[tile['crop']]['first_yield_day']:near['HARVEST']+=1
                if near:
                    counts['uncommitted_pass_with_reachable_service']+=1
                    for k in near:counts['idle_with_'+k]+=1
                    if len(samples)<12:samples.append({'step':t,'unit':i,'position':pos,'reachable_jobs':dict(near)})
        return original(farm,private,i,action,*args,**kwargs)
    eng._apply_unit_action=apply
    try:
        for t in range(719):
            now[0]=t;obs=copy.deepcopy(env.state[1].observation);obs['step']=t;env.step([saved['trace'][t]['action'],other(obs)]);assert env.state[0].observation.farms[0]['money']==saved['trace'][t]['cash']
    finally:eng._apply_unit_action=original
    assert [float(s.reward) for s in env.state]==[saved['own_cash'],saved['opponent_cash']]
    r={'version':version,'seed':seed,'exact_719_cash_and_final_rewards':True,'counts':dict(counts),'caveat':'Overlapping per-worker opportunities, not unique jobs or achievable counterfactual profit. CARE may need FEED to realize production bonus; work not reserved here.','samples':samples}
    (B/'diagnostics'/f'{version}_{seed}_idle_jobs.json').write_text(json.dumps(r,indent=2)+'\n');return {k:v for k,v in r.items() if k not in ['samples','caveat']}
if __name__=='__main__':
    version=sys.argv[1];tasks=[(version,s) for s in range(919260010,919260014)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,tasks))
    (B/'diagnostics'/f'idle_jobs_{version}_summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
