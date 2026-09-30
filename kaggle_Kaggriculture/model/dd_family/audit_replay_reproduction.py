"""Replay both recorded agents in the installed official engine; compare every state."""
from pathlib import Path
import contextlib,copy,hashlib,io,json,sys,concurrent.futures
B=Path(__file__).resolve().parent

def differences(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):
  for key in set(a)|set(b):
   if key not in a or key not in b:return {'path':path+'/'+key,'local':a.get(key),'replay':b.get(key)}
   diff=differences(a[key],b[key],path+'/'+key)
   if diff:return diff
 elif isinstance(a,list) and isinstance(b,list):
  if len(a)!=len(b):return {'path':path+'/length','local':len(a),'replay':len(b)}
  for i,(x,y) in enumerate(zip(a,b)):
   diff=differences(x,y,path+'/'+str(i))
   if diff:return diff
 elif a!=b:return {'path':path,'local':a,'replay':b}
 return None

def run(k):
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from kaggle_environments import make
 m=json.loads((B/'ddm/training_manifest.json').read_text());row=m['episodes'][k];source=Path(row['path']);assert hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256'];replay=json.loads(source.read_text())
 config=dict(replay['configuration']);config['seed']=replay['info']['seed'];env=make('kaggriculture',configuration=config);env.reset(2)
 first=None;checked=0
 for t in range(719):
  env.step([copy.deepcopy(state['action']) for state in replay['steps'][t+1]])
  for seat in [0,1]:
   ref=dict(replay['steps'][t+1][0]['observation']);ref.update(replay['steps'][t+1][seat]['observation']);live=env.state[seat].observation
   for key in ['farms','private','market','town','day','hour']:
    diff=differences(live[key],ref[key],key)
    if diff and first is None:first={'step':t+1,'seat':seat,**diff}
    checked+=1
 rewards=[float(s.reward) for s in env.state]
 out={'prototype':k,'episode_id':row['episode_id'],'source_sha256':row['sha256'],'replay_module_version':replay['module_version'],'checks':checked,'first_state_difference':first,'local_rewards':rewards,'replay_rewards':replay['rewards'],'exact_rewards':rewards==replay['rewards']}
 return out
if __name__=='__main__':
 indices=list(map(int,sys.argv[1:])) or [35,0,79,124]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,indices))
 (B/'audit_replay_reproduction.json').write_text(json.dumps(rows,indent=2)+'\n')
 for r in rows:print(json.dumps(r))
