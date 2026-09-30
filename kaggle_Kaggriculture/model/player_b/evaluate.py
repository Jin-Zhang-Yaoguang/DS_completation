"""自然规则、每局独立 raw-loader 入口、不可静默异常的对战器。"""
import sys, json, hashlib, time, statistics, argparse, traceback, os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
HERE=Path(__file__).resolve().parent
ENGINE=Path('/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/engine_parity_failure/slotfix_build_v2')
sys.path.insert(0,str(ENGINE))
import kagsim_slotfix as kagsim

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(path):
    ns={'__name__':'player_b_runtime','__file__':str(path)}
    exec(compile(Path(path).read_text(),str(path),'exec'),ns)
    f=[v for k,v in ns.items() if callable(v) and not k.startswith('__')][-1]
    return f,ns

def play(job):
    c,op,seed,seat,cp,opp=job
    row={'candidate':c,'opponent':op,'seed':seed,'seat':seat}
    try:
        a,n=load(cp); b,_=load(opp); agents=[None,None]; agents[seat]=a; agents[1-seat]=b
        game=kagsim.Game(seed); calls=0; max_ms=0; start=time.monotonic()
        while not game.done:
            obs=[game.observe(0),game.observe(1)]; acts=[]
            for s in (0,1):
                t=time.perf_counter(); x=agents[s](obs[s]); dt=(time.perf_counter()-t)*1000
                if s==seat: max_ms=max(max_ms,dt)
                if not isinstance(x,dict) or len(x.get('market',[]))>10: raise RuntimeError('invalid action')
                acts.append(x)
            game.step(*acts);calls+=1
        rewards=[float(game.reward(s)) for s in (0,1)]
        row.update(status='DONE',calls=calls,bank=rewards[seat],other=rewards[1-seat],margin=rewards[seat]-rewards[1-seat],win=int(rewards[seat]>rewards[1-seat]),max_ms=max_ms,seconds=time.monotonic()-start,mechanism=n.get('_B_STATS',{}))
        if calls!=719: raise RuntimeError('unexpected calls')
    except Exception:
        row.update(status='ERROR',error=traceback.format_exc())
    return row

def summarize(rows):
    out={}
    for c,o in sorted(set((r['candidate'],r['opponent']) for r in rows)):
        rs=[r for r in rows if r['candidate']==c and r['opponent']==o];ok=[r for r in rs if r['status']=='DONE']
        out[c+' vs '+o]={'games':len(rs),'errors':len(rs)-len(ok),'wins':sum(r['win'] for r in ok),'ties':sum(r['margin']==0 for r in ok),'winrate':sum(r['win'] for r in ok)/len(rs),'margin':statistics.mean([r['margin'] for r in ok]) if ok else None,'max_ms':max([r['max_ms'] for r in ok],default=0)}
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--count',type=int,default=8);p.add_argument('--candidates',default='b1,v54d');p.add_argument('--opponents',default='v54c,v53e,v19a,v120');p.add_argument('--workers',type=int,default=4);args=p.parse_args()
    run=HERE/'runs'/args.run;run.mkdir(parents=True,exist_ok=True)
    if (run/'manifest.json').exists(): raise RuntimeError('run already exists: no duplicate')
    seeds=[int.from_bytes(hashlib.sha256(('player-b-'+args.run+':'+str(i)).encode()).digest()[:4],'big')&0x7fffffff for i in range(args.count)]
    paths={n: HERE/('candidates' if n.startswith('b') else 'sources')/n/'main.py' for n in set(args.candidates.split(',')+args.opponents.split(','))}
    manifest={'seeds':seeds,'paths':{n:str(p) for n,p in paths.items()},'sha256':{n:sha(p) for n,p in paths.items()},'engine':str(kagsim.__file__),'engine_sha256':sha(kagsim.__file__),'natural_shops':True,'entrypoint':'last non-dunder callable in raw source order','time':time.time()}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2))
    jobs=[(c,o,s,seat,str(paths[c]),str(paths[o])) for c in args.candidates.split(',') for o in args.opponents.split(',') if c!=o for s in seeds for seat in (0,1)]
    rows=[]
    with (run/'games.jsonl').open('w') as f,ProcessPoolExecutor(args.workers) as ex:
        for fut in as_completed([ex.submit(play,j) for j in jobs]):
            row=fut.result();rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
            if len(rows)%32==0 or row['status']=='ERROR':print(f'{len(rows)}/{len(jobs)} '+(row.get('error','')),flush=True)
    for n,p in paths.items():
        if sha(p)!=manifest['sha256'][n]:raise RuntimeError('source drift')
    summary=summarize(rows);(run/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
