import subprocess,concurrent.futures,pathlib
refs=['najiama/xgboost-triple-te-dynamic-pruning-lb-0-94639','yekenot/ps-s6-e9-realmlp-pytorch','ern711/rpu-a-flexible-relational-pattern-unit','megayak/s6e9-four-feature-views-one-ensemble-lb-0-94639']
def f(ref):
 dest=pathlib.Path('/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/competition_description/forum_review_20260913/evidence/code')/ref/'outputs';dest.mkdir(parents=True,exist_ok=True)
 r=subprocess.run(['kaggle','kernels','output',ref,'-p',str(dest),'--file-pattern',r'(^|/)([^/]*summary[^/]*\.csv|[^/]*summary[^/]*\.json|[^/]*\.log)$'],capture_output=True,text=True,timeout=100)
 return ref,r.returncode,r.stdout[-1300:],r.stderr[-200:]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
 for r in ex.map(f,refs):print(r,flush=True)
