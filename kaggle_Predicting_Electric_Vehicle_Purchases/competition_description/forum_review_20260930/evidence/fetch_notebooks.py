from __future__ import annotations
import concurrent.futures,json,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent
refs=['heuljax/kps6e09-generator-aware-ridge-logistic-regression','heuljax/kps6e09-logistic-regression-sample','abhirajhiwale/s6e9-0-94677-ridge-tower-4-stable-rules','lucifer19/ev-grand-prix-48-engine-cpu-pit-stop-blend','souvikdbiswas/geodesic-rank-manifold-0-94679-fast-ev-ensemble','nina2025/fork-of-ps-s6e9','goodpjw2008/s6e9-lr-margin-gbdt-oof-stack-lb-0-94675','mikhailnaumov/electric-vehicle-purchases-single-xgb','megayak/s6e9-reading-and-fitting-the-public-split','ou20040313/s6e9-single-model-alternatives']
def fetch(ref):
 dest=OUT/'code'/ref;dest.mkdir(parents=True,exist_ok=True);results=[]
 for args in [['kernels','pull',ref,'-p',str(dest),'-m'],['kernels','output',ref,'-p',str(dest/'outputs'),'--file-pattern',r'(^|/)([^/]*summary[^/]*\.csv|[^/]*summary[^/]*\.json|[^/]*\.log)$']]:
  try:
   r=subprocess.run(['/Users/a1-6/.local/bin/kaggle',*args],capture_output=True,text=True,timeout=180);results.append({'command':args[:3],'returncode':r.returncode,'stdout':r.stdout[-1200:],'stderr':r.stderr[-1000:]})
  except Exception as e:results.append({'error':str(e)})
 for p in dest.glob('*.ipynb'):
  nb=json.loads(p.read_text());parts=[];outputs=[]
  for i,c in enumerate(nb.get('cells',[])):
   parts.append(f'# CELL {i} {c.get("cell_type")}\n'+''.join(c.get('source',[])))
   for o in c.get('outputs',[]):
    if 'text' in o:outputs.append(''.join(o['text']))
    if 'data' in o and 'text/plain' in o['data']:outputs.append(''.join(o['data']['text/plain']))
  (dest/'source.readable.txt').write_text('\n\n'.join(parts));(dest/'embedded_outputs.txt').write_text('\n'.join(outputs))
 return {'ref':ref,'results':results}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 rows=list(pool.map(fetch,refs))
(OUT/'notebook_fetch_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print(json.dumps(rows,ensure_ascii=False,indent=2))
