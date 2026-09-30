from pathlib import Path
import json,re,subprocess,concurrent.futures,datetime
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RAW=HERE/'raw'
K='/Users/a1-6/.local/bin/kaggle'
def cli(args,name):
 p=subprocess.run([K,'competitions',*args,'--format','json'],capture_output=True,text=True,timeout=120)
 (RAW/name).write_text(p.stdout)
 if p.returncode: raise RuntimeError(p.stderr)
 for m in re.finditer(r'[\[{]',p.stdout):
  try:return json.JSONDecoder().raw_decode(p.stdout[m.start():])[0]
  except ValueError:pass
 raise ValueError(name)
def header(p):
 try:
  with p.open('rb') as f:s=f.read(65536).decode('utf8','ignore')
  if 'Majkel1337' not in s:return None
  eid=re.search(r'"EpisodeId"\s*:\s*(\d+)',s)
  names=re.search(r'"TeamNames"\s*:\s*(\[[^\]]*\])',s)
  if eid and names:return {'episode_id':int(eid[1]),'path':str(p.resolve()),'teams':json.loads(names[1]),'source':'local_archive'}
 except OSError:pass
if __name__=='__main__':
 lb=cli(['leaderboard','kaggriculture','--show','--page-size','20'],'leaderboard.txt')
 subs=cli(['team-submissions','16718819'],'team_submissions.txt')
 episodes={}
 for sub in subs:
  rows=cli(['episodes',str(sub['id'])],f"episodes_{sub['id']}.json")
  episodes[str(sub['id'])]=rows
  print('submission',sub,'episodes',len(rows),flush=True)
 (RAW/'snapshot.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'leaderboard':lb,'submissions':subs,'episodes':episodes},indent=2))
 paths=list((ROOT/'kaggle_Kaggriculture/model_data/kaggriculture_episodes_index').glob('date=*/data/*.json'))
 print('scan',len(paths),flush=True)
 found=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
  for r in ex.map(header,paths):
   if r:found.append(r)
 (RAW/'local_inventory.json').write_text(json.dumps(found,indent=2))
 print('local_found',len(found),flush=True)
