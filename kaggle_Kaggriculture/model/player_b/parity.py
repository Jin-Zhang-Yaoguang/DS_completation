"""官方路径加载器与修复快引擎逐帧对照。"""
import contextlib,io,sys,json,copy,hashlib,time,argparse
from pathlib import Path
import evaluate as ev
buf=io.StringIO()
with contextlib.redirect_stdout(buf),contextlib.redirect_stderr(buf):
    from kaggle_environments import make
    from kaggle_environments.agent import get_last_callable
    import kaggle_environments
FIELDS=('player','day','hour','step','farms','private','market','town')

def diff(a,b,p=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            if k not in a or k not in b:return p+'.'+k+' missing'
            d=diff(a[k],b[k],p+'.'+k)
            if d:return d
    elif isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
        if len(a)!=len(b):return p+' length'
        for i,(x,y) in enumerate(zip(a,b)):
            d=diff(x,y,p+f'[{i}]')
            if d:return d
    elif a!=b:return p+': '+repr(a)[:120]+' != '+repr(b)[:120]
    return None

if __name__=='__main__':
    pa=argparse.ArgumentParser();pa.add_argument('--candidate',default='b2');pa.add_argument('--out',default='parity');args=pa.parse_args()
    out=ev.HERE/'runs'/args.out;out.mkdir(exist_ok=True);rows=[]
    for seed in (1938217,93527141):
      for seat in (0,1):
        paths=[ev.HERE/'candidates'/args.candidate/'main.py',ev.HERE/'sources/v54d/main.py']
        if seat: paths.reverse()
        af=[ev.load(p)[0] for p in paths]
        ag=[get_last_callable(p.read_text(),path=str(p)) for p in paths]
        engine=ev.kagsim.Game(seed)
        official=make('kaggriculture',configuration={'seed':seed,'episodeSteps':720},debug=False);official.reset(2)
        calls=0;checks=0;start=time.monotonic();error=None
        try:
          while True:
            obs=[engine.observe(s) for s in (0,1)]
            oo=[copy.deepcopy(dict(official._Environment__get_shared_state(s).observation)) for s in (0,1)]
            for s in (0,1):
              for f in FIELDS:
                d=diff(obs[s].get(f),oo[s].get(f),f)
                if d: raise RuntimeError(f'step={calls} seat={s} '+d)
              checks+=1
            if engine.done:break
            aa=[af[s](obs[s]) for s in (0,1)];ba=[ag[s](oo[s],official.configuration) for s in (0,1)]
            if aa!=ba:raise RuntimeError(f'raw-loader action mismatch at {calls}')
            engine.step(*aa);official.step(ba);calls+=1
          assert [str(s.status) for s in official.state]==['DONE','DONE']
          assert [float(engine.reward(s)) for s in (0,1)]==[float(s.reward) for s in official.state]
        except Exception as e:error=repr(e)
        row={'seed':seed,'seat':seat,'candidate':args.candidate,'calls':calls,'state_checks':checks,'error':error,'seconds':time.monotonic()-start,'status':'PASS' if error is None and calls==719 else 'FAIL','rewards':[float(s.reward or 0) for s in official.state]}
        rows.append(row);print(json.dumps(row),flush=True)
    result={'version':kaggle_environments.__version__,'rows':rows,'sha256':{str(p):ev.sha(p) for p in paths},'all_pass':all(r['status']=='PASS' for r in rows),'runtime':'official get_last_callable + step interpreter; Kaggle sandbox not emulated'}
    (out/'report.json').write_text(json.dumps(result,indent=2))
