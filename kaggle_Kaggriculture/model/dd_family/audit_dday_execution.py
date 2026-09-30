"""Audit realized perennial program harvests in identical dynamic matches."""
from pathlib import Path
import concurrent.futures,contextlib,copy,gzip,hashlib,io,json,sys
B=Path(__file__).resolve().parent

def run(seed):
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(B/'dday'));import main,action_space as space,rules
    policy=main.Agent();base=json.load(gzip.open(B/'dday/runs/dev01/games'/f'y68v_{seed}_0.json.gz','rt'))
    op=next(o for o in json.loads((B/'protocol.json').read_text())['opponents'] if o['name']=='y68v');path=B/op['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2);records={}
    for t in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        action=policy.act(obs[0]);assert action==base['trace'][t]['action'];shadow=copy.deepcopy(obs[0])
        for i,a in enumerate([action['farmer'],*action['hands']]):
            entry=policy.perennial.data['units'].get(f'{t}:{i}');before=copy.deepcopy(shadow['private']['inventories'][i]);xy=space.unit_position(shadow,i)
            rules._apply_unit_action(shadow['farms'][0],shadow['private'],i,a,10,t//24,24,100)
            if entry is None or entry[0] not in policy.perennial.selected:continue
            j,ix=entry;job=policy.perennial.data['jobs'][j];p=policy.perennial.selected[j]
            r=records.setdefault(j,{'job':j,'original':job['crop'],'selected':p['crop'],'expected_units':p['yield_units'],'actual_units':0,'planted':False,'position_mismatches':0,'events':[]})
            gain=shadow['private']['inventories'][i].get(p['crop'],0)-before.get(p['crop'],0)
            r['actual_units']+=max(0,gain);r['position_mismatches']+=list(xy)!=job['xy']
            tile=shadow['farms'][0]['tiles'][xy[1]][xy[0]]
            if ix==0:r['planted']=isinstance(tile,dict) and tile.get('crop')==p['crop']
            r['events'].append({'step':t,'unit':i,'action':a,'gain':gain,'tile_after':tile})
        env.step([action,other(obs[1])]);assert env.state[0].observation.farms[0]['money']==base['trace'][t]['cash']
    return {'seed':seed,'rewards':[s.reward for s in env.state],'records':list(records.values()),'exact_match':True}

if __name__=='__main__':
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,[919260010,919260011,919260012,919260013]))
    (B/'audit_dday_execution.json').write_text(json.dumps(rows,indent=2)+'\n')
    for r in rows:print(json.dumps({'seed':r['seed'],'jobs':[{k:v for k,v in x.items() if k!='events'} for x in r['records']]}),flush=True)
