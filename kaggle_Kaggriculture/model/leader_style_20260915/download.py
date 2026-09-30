from pathlib import Path
import json,subprocess,concurrent.futures,datetime,time
B=Path(__file__).resolve().parent;R=B/'raw';D=B/'replays';D.mkdir(exist_ok=True)
s=json.loads((R/'snapshot.json').read_text());inv={r['episode_id']:r for r in json.loads((R/'local_inventory.json').read_text())}
meta={}
for sid,rows in s['episodes'].items():
 for r in rows:
  if 'PUBLIC' in r['type'] and 'COMPLETED' in r['state']:
   meta.setdefault(r['id'],dict(r,submission_ids=[]))['submission_ids'].append(int(sid))
# Search other local replay archives by exact filename; avoid scanning large contents.
root=B.parents[2]/'kaggle_Kaggriculture'
missing=set(meta)-set(inv)
for base in [root/'model_data',root/'model/community_research']:
 for p in base.rglob('episode-*-replay.json'):
  try:eid=int(p.name.split('-')[1])
  except ValueError:continue
  if eid in missing and p.exists():inv[eid]={'episode_id':eid,'path':str(p.resolve()),'source':'other_local_archive'};missing.discard(eid)
print('public',len(meta),'reuse',len(set(meta)&set(inv)),'download',len(missing),flush=True)
def get(eid):
 p=D/f'episode-{eid}-replay.json';errors=[]
 if p.exists() and p.stat().st_size>100000:return {'episode_id':eid,'path':str(p),'source':'downloaded'}
 for attempt in range(3):
  try:
   r=subprocess.run(['/Users/a1-6/.local/bin/kaggle','competitions','replay',str(eid),'-p',str(D),'-q'],capture_output=True,text=True,timeout=180)
   if r.returncode==0 and p.exists():return {'episode_id':eid,'path':str(p),'source':'downloaded'}
   errors.append((r.stderr or r.stdout)[-600:])
  except subprocess.TimeoutExpired:errors.append('timeout')
  time.sleep(2*(attempt+1))
 return {'episode_id':eid,'error':errors}
errors=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for n,r in enumerate(ex.map(get,sorted(missing)),1):
  if 'path' in r:inv[r['episode_id']]=r
  else:errors.append(r)
  if n%10==0:print('downloaded progress',n,'/',len(missing),'errors',len(errors),flush=True)
  (R/'download_progress.json').write_text(json.dumps({'done':n,'total':len(missing),'errors':errors,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}))
for eid,r in inv.items():r['metadata']=meta.get(eid);r['panel']='active_public' if eid in meta else 'historical_daily'
(R/'inventory.json').write_text(json.dumps({'rows':list(inv.values()),'errors':errors,'public_unique':len(meta),'at':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2))
print('finished',len(inv),'errors',len(errors),flush=True)
