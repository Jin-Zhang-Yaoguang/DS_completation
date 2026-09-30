"""Attribute successful non-ongoing crop harvests and remaining same-day water growth."""
from pathlib import Path
import argparse,collections,concurrent.futures,contextlib,copy,gzip,hashlib,importlib,io,json,sys
B=Path(__file__).resolve().parent

def run(task):
    version,seed=task;seat=0
    with gzip.open(B/version/'runs/development01/games'/f'y68v_{seed}_0.json.gz','rt') as f:saved=json.load(f)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
        eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    op=next(r for r in json.loads((B/'protocol.json').read_text())['opponents'] if r['name']=='y68v');path=B/op['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2);events=[];now=[0];original=eng._apply_unit_action
    def apply(farm,private,i,action,*args,**kwargs):
        player=sys._getframe(1).f_locals['i'];x,y=eng._farmer_position(farm,i);tile=copy.deepcopy(farm['tiles'][y][x]);result=original(farm,private,i,action,*args,**kwargs)
        if player==seat and action[0]=='HARVEST' and isinstance(tile,dict) and tile.get('crop') and farm['tiles'][y][x]!=tile:
            day=now[0]//24;rule=eng.CROPS[tile['crop']]
            if not rule['ongoing']:
                age=day-tile['planted_day'];bonus=2 if tile.get('fertilized_until_day',-1)>=day else 1
                opportunity=not tile.get('watered_today') and (rule['max_yield_day']+1)//2<=age<=rule['max_yield_day'] and tile.get('yield_units',0)<rule['max_yield'] and now[0]%24<23 and now[0]<718
                events.append({'step':now[0],'day':day,'unit':i,'xy':[x,y],'crop':tile['crop'],'age':age,'yield_units':tile.get('yield_units',0),'watered_today':tile.get('watered_today'),'same_day_water_opportunity':opportunity,'extra_units_upper_bound':min(bonus,rule['max_yield']-tile.get('yield_units',0)) if opportunity else 0})
        return result
    eng._apply_unit_action=apply
    try:
        for t in range(719):
            now[0]=t;obs=copy.deepcopy(env.state[1].observation);obs['step']=t;env.step([saved['trace'][t]['action'],other(obs)]);assert env.state[0].observation.farms[0]['money']==saved['trace'][t]['cash']
    finally:eng._apply_unit_action=original
    assert [float(s.reward) for s in env.state]==[saved['own_cash'],saved['opponent_cash']]
    summary={'version':version,'seed':seed,'exact_719_cash_and_rewards':True,'single_crop_harvests':len(events),'before_daily_water_in_growth_window':sum(r['same_day_water_opportunity'] for r in events),'extra_units_upper_bound':sum(r['extra_units_upper_bound'] for r in events),'by_crop':dict(collections.Counter(r['crop'] for r in events))}
    (B/'diagnostics'/f'{version}_{seed}_harvest_water.json').write_text(json.dumps({**summary,'events':events},indent=2)+'\n');return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('versions',nargs='+');a=ap.parse_args();tasks=[(v,s) for v in a.versions for s in range(919260010,919260014)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,tasks))
    (B/'diagnostics'/('harvest_water_'+'_'.join(a.versions)+'_summary.json')).write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
