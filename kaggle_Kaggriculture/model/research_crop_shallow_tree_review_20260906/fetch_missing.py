import concurrent.futures,json,subprocess,datetime
from pathlib import Path
b=Path(__file__).resolve().parent
d=json.loads((b/'replay_inventory.json').read_text());out=b/'replays';out.mkdir(exist_ok=True)
def fetch(e):
 p=out/f'episode-{e}-replay.json'
 if p.exists():return e,True
 try:
  r=subprocess.run(['/Users/a1-6/.local/bin/kaggle','competitions','replay',str(e),'--path',str(out),'--quiet'],capture_output=True,text=True,timeout=90)
  return e,r.returncode==0 and p.exists()
 except subprocess.TimeoutExpired:return e,False
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
 for result in ex.map(fetch,d['missing']):
  results.append(result)
  if len(results)%20==0:print(f'completed {len(results)}/{len(d["missing"])}; successful {sum(x[1] for x in results)}',flush=True)
(b/'fetch_result.json').write_text(json.dumps({'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results},indent=2));print('done',len(results),sum(x[1] for x in results),flush=True)
