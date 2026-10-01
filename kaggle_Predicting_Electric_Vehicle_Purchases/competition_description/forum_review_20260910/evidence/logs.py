import subprocess,concurrent.futures,pathlib
refs=['ern711/hierarchical-prototype-matching-network','yekenot/ps-s6-e9-realmlp-pytorch','najiama/pure-lgbm-model-cv-0-94606-lb-0-94637','ern711/replication-aware-newton-boosting','maiernator/s6e9-ctboost-not-catboost-astra-baseline']
def f(ref):
 dest=pathlib.Path('/tmp/s6e9_forum_20260910/code')/ref/'outputs';dest.mkdir(parents=True,exist_ok=True)
 r=subprocess.run(['kaggle','kernels','output',ref,'-p',str(dest),'--file-pattern',r'(^|/)([^/]*summary[^/]*\.csv|[^/]*summary[^/]*\.json|[^/]*\.log)$'],capture_output=True,text=True,timeout=100)
 return ref,r.returncode,r.stdout[-1300:],r.stderr[-200:]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for r in ex.map(f,refs):print(r,flush=True)
