import subprocess,concurrent.futures,pathlib
refs=['ern711/hierarchical-prototype-matching-network','yekenot/ps-s6-e9-realmlp-pytorch','najiama/pure-lgbm-model-cv-0-94606-lb-0-94637','najiama/oof-power-two-single-models-blend-lb-0-94638','talhatursun/s6e9-daily-rank-average-ensemble','jazivxt/single-model-zoom-zoom']
def f(ref):
 dest=pathlib.Path('/tmp/s6e9_forum_20260910/code')/ref.split('/')[0]/ref.split('/')[1];dest.mkdir(parents=True,exist_ok=True)
 r=subprocess.run(['kaggle','kernels','pull',ref,'-p',str(dest),'-m'],capture_output=True,text=True,timeout=100)
 return ref,r.returncode,r.stdout,r.stderr[-300:]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for r in ex.map(f,refs): print(r,flush=True)
