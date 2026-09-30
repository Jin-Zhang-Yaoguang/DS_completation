"""Check unused collectible fertilizer after replay workers finish their daily duties."""
from pathlib import Path
import collections,concurrent.futures,contextlib,copy,gzip,hashlib,io,json,sys
import numpy as np
B=Path(__file__).resolve().parent
def run(seed):
    sys.path.insert(0,str(B/'ddam'));import action_space as A,rules,labor
    arr={p.stem:np.load(p,mmap_mode='r') for p in (B/'ddam/data').glob('*.npy')};k=35;dispatch=labor.Dispatcher(arr,k);planned=collections.defaultdict(list)
    for t in range(719):
        for i,tok in enumerate(arr['unit_tokens'][t,k]):
            if int(tok)==A.UNIT_INDEX['COLLECT_FERTILIZER']:
                xy=tuple(round(float(n)*9) for n in arr['units'][t,k,i,2:4]);planned[t//24,xy].append(t)
    with gzip.open(B/f'ddam/runs/broad01/games/y68v_{seed}_0.json.gz','rt') as f:saved=json.load(f)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    op=next(x for x in json.loads((B/'protocol.json').read_text())['opponents'] if x['name']=='y68v');p=B/op['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(p.read_text(),path=str(p));env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);counts=collections.Counter();daily=[];examples=[];opportunities=set()
    for t in range(719):
        obs=copy.deepcopy(env.state[0].observation);obs['step']=t;shadow=copy.deepcopy(obs);farm=A.own_farm(shadow);private=shadow['private'];a=saved['trace'][t]['action'];day=t//24;end=min(day*24+24,719)
        for i,order in enumerate([a['farmer'],*a['hands']]):
            if order[0]=='PASS' and t>dispatch.ends.get((day,i),t) and t>dispatch.last_hire[day]:
                counts['eligible_pass']+=1;paths=dispatch.paths(farm,A.unit_position(shadow,i));held=sum(private['shed'].values())+sum(sum(v.values()) for v in private['inventories']);jobs=[]
                for y,row in enumerate(farm['tiles']):
                    for x,tile in enumerate(row):
                        if not isinstance(tile,dict) or not tile.get('animal') or not tile.get('fertilizer_available') or (x,y) not in paths:continue
                        if any(tt>=t for tt in planned[day,(x,y)]):continue
                        distance=len(paths[x,y]);deposit=min(abs(x-sx)+abs(y-sy) for sx,sy in A.SHED_ACCESS)+1 if day==29 else 0
                        if distance+1+deposit>end-t or held+1>95:continue
                        jobs.append((x,y));opportunities.add((day,x,y))
                if jobs:
                    counts['eligible_pass_with_collectible_fert']+=1
                    if len(examples)<12:examples.append({'step':t,'unit':i,'position':A.unit_position(shadow,i),'targets':jobs,'price':obs['market']['prices']['FERTILIZER']})
            rules._apply_unit_action(farm,private,i,order,10,day,24,100)
        if t%24==23:
            tiles=[v for row in farm['tiles'] for v in row if isinstance(v,dict) and v.get('animal')];daily.append({'day':day,'animals':len(tiles),'fert_uncollected':sum(bool(v.get('fertilizer_available')) for v in tiles),'price':obs['market']['prices']['FERTILIZER']})
        o=copy.deepcopy(env.state[1].observation);o['step']=t;env.step([a,other(o)]);assert env.state[0].observation.farms[0]['money']==saved['trace'][t]['cash']
    assert [float(s.reward) for s in env.state]==[saved['own_cash'],saved['opponent_cash']]
    result={'seed':seed,'version':'ddam','exact_719_cash_and_both_rewards':True,'counts':dict(counts),'unique_animal_day_opportunities':len(opportunities),'total_uncollected_fert_at_close':sum(r['fert_uncollected'] for r in daily),'daily':daily,'examples':examples,'caveat':'Overlapping reachable opportunities, not achieved extra production or profit.'};(B/'diagnostics'/f'ddam_{seed}_spare_fert.json').write_text(json.dumps(result,indent=2)+'\n');return {k:v for k,v in result.items() if k not in ['daily','examples']}
if __name__=='__main__':
    seeds=[919261002,919261005,919262004,919262007]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,seeds))
    (B/'diagnostics/ddam_spare_fert_summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
