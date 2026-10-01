import subprocess,concurrent.futures,pathlib
refs=['maiernator/s6e9-ctboost-not-catboost-astra-baseline','vishal567/s6e9-what-actually-moves-auc-an-honest-ablation','amirhosseinkarimiee/the-noise-bar-feature-engineering','megayak/s6e9-lb-0-94643-and-six-missing-sources','miickey/s6e9-kaggle-ready-0-94644-micro-blend','nina2025/ps-s6e9-ensemble-new-engine-4','ern711/replication-aware-newton-boosting','amirhosseinkarimiee/predicting-ev-purchases-s6e9']
def f(ref):
 dest=pathlib.Path('/tmp/s6e9_forum_20260910/code')/ref.split('/')[0]/ref.split('/')[1];dest.mkdir(parents=True,exist_ok=True)
 r=subprocess.run(['kaggle','kernels','pull',ref,'-p',str(dest),'-m'],capture_output=True,text=True,timeout=100)
 return ref,r.returncode,r.stdout,r.stderr[-300:]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for r in ex.map(f,refs): print(r,flush=True)
