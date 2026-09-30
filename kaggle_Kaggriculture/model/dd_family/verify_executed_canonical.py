"""Independent full-state verification of canonical requests for both players."""
from pathlib import Path
import concurrent.futures,contextlib,copy,hashlib,io,json,sys
import numpy as np
B=Path(__file__).resolve().parent

def verify(k):
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from kaggle_environments import make
 sys.path.insert(0,str(B/'dde'));import action_space as a
 row=json.loads((B/'dde/training_manifest.json').read_text())['episodes'][k];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat'];cfg=dict(rep['configuration']);cfg['seed']=rep['info']['seed'];env=make('kaggriculture',configuration=cfg);env.reset(2)
 path=B/'executed_new_teacher'/f'{k:03}_effective.npz'
 with np.load(path) as z:ar={n:z[n].copy() for n in z.files}
 checks=0
 for t in range(719):
  n=1+len(env.state[seat].observation.farms[seat]['hands']);units=[]
  for i in range(n):
   parts=a.UNIT_TOKENS[int(ar['unit_tokens'][t,i])].split(':')
   if parts[0] in ['PICKUP','PLACE']:parts.append(int(ar['unit_quantities'][t,i]))
   units.append(parts)
  market=[]
  for tok,q in zip(ar['market_tokens'][t],ar['market_quantities'][t]):
   if not tok:break
   parts=a.MARKET_TOKENS[int(tok)].split(':')
   if len(parts)==2:parts.append(int(q))
   market.append(parts)
  acts=[copy.deepcopy(s['action']) for s in rep['steps'][t+1]];acts[seat]={'farmer':units[0],'hands':units[1:],'market':market};env.step(acts)
  for player in [0,1]:
   expected=dict(rep['steps'][t+1][0]['observation']);expected.update(rep['steps'][t+1][player]['observation'])
   for field in ['farms','private','market','town','day','hour']:
    assert env.state[player].observation[field]==expected[field],(k,t,player,field);checks+=1
 rewards=[float(s.reward) for s in env.state];assert rewards==rep['rewards']
 return {'prototype':k,'episode_id':row['episode_id'],'checks':checks,'both_private_states_verified':True,'effective_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_sha256':row['sha256'],'rewards':rewards}
if __name__=='__main__':
 rows=[]
 for start in range(0,121,24):
  with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
   for r in pool.map(verify,range(start,min(start+24,121))):
    rows.append(r)
    if len(rows)%20==0:print('verified',len(rows),flush=True)
 out={'plans':len(rows),'field_checks':sum(r['checks'] for r in rows),'all_exact':True,'engine':'1.32.7','rows':rows,'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (B/'audit_executed_canonical_all_states.json').write_text(json.dumps(out,indent=2)+'\n');print('all exact',len(rows),out['field_checks'],flush=True)
