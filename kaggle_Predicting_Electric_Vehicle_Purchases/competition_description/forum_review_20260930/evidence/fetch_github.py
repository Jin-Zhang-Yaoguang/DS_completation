from __future__ import annotations
import base64,concurrent.futures,datetime,json,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent

def gh(args):
 r=subprocess.run(['gh',*args],capture_output=True,text=True,timeout=90)
 if r.returncode:raise RuntimeError(r.stderr[:500])
 return json.loads(r.stdout)
def save(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
allrepos={}
for k,q in [('s6e9','s6e9'),('title','"Predicting Electric Vehicle Purchases"'),('ev','"electric vehicle" kaggle')]:
 rows=gh(['search','repos',q,'--limit','100','--sort','updated','--json','fullName,description,url,updatedAt']);save('github_search_'+k+'.json',rows)
 for row in rows:allrepos[row['fullName']]=row
save('github_search_all.json',list(allrepos.values()))
selected=['OpenKaggle/playground-series-s6e9-research','graphedge/playground-series-s6e9','oivler/kaggle-electric-vehicle-purchases','Atlas-Black/playground-series-s6e9','bawdiest/k_s6e9','gccarno/kaggle_playground_s6e9','dailycodepython/Kaggle-S6E9-EV-Rank-Ensemble','happyc0der/kaggle-s6e9-ev-purchases','canaryigo/kaggle-s6e9-ev-purchase-prediction','Agnuxo1/s6e9-honest-ceiling','najiucdb/s6e9-leaderboard-tracker','andrewleal0412-arch/s6e9-experiments']
def fetch(repo):
 out=OUT/'github'/repo.replace('/','__');out.mkdir(parents=True,exist_ok=True)
 try:
  metadata=gh(['api',f'repos/{repo}']);commit=gh(['api',f'repos/{repo}/commits/{metadata["default_branch"]}']);sha=commit['sha'];tree=gh(['api',f'repos/{repo}/git/trees/{sha}?recursive=1'])
  for name,data in [('metadata.json',metadata),('commit.json',commit),('tree.json',tree)]: (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
  files=[t['path'] for t in tree['tree'] if t['type']=='blob'];readmes=[p for p in files if p.lower() in ('readme.md','readme.rst','readme')]
  if readmes:
   content=gh(['api',f'repos/{repo}/contents/{readmes[0]}?ref={sha}']);(out/'README.md').write_bytes(base64.b64decode(content['content']))
  return {'repo':repo,'sha':sha,'files':len(files),'updated_at':metadata['updated_at'],'pushed_at':metadata['pushed_at'],'status':'OK'}
 except Exception as e:return {'repo':repo,'status':'ERROR','error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(fetch,selected))
save('github_fetch_results.json',results);save('github_retrieval.json',{'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'search_unique':len(allrepos),'selected':len(selected),'results':results})
print(json.dumps(results,ensure_ascii=False,indent=2))
