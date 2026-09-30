"""Episode/seed-disjoint BC corpus from the frozen Majkel PUBLIC replay panel."""
from pathlib import Path
import json,hashlib,concurrent.futures,collections,time
import numpy as np
import contract,action_space as space
B=Path(__file__).resolve().parent;SOURCE=B.parent/'leader_style_20260915';D=B/'data';D.mkdir(exist_ok=True);(D/'episodes').mkdir(exist_ok=True)
def one(r):
 dst=D/'episodes'/f"{r['episode_id']}.npz"
 if dst.exists():return r['episode_id']
 raw=Path(r['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256'];replay=json.loads(raw);seat=r['seat'];arrays=collections.defaultdict(list);unknown=0
 for i in range(719):
  obs=replay['steps'][i][seat]['observation'];action=replay['steps'][i+1][seat]['action'];assert obs.get('step',i)==i;obs['step']=i
  x=contract.encode(obs);a=space.encode_action(obs,action);n=space.unit_count(obs);assert n<=16
  unknown+=sum(not v for v in a['unit_known'])+sum(not v for v in a['market_known'])
  for k,v in x.items():arrays[k].append(v)
  for k in ['unit_tokens','unit_quantities']:arrays[k].append(np.pad(np.asarray(a[k],np.int16),(0,16-n)))
  for k in ['market_tokens','market_quantities']:arrays[k].append(np.asarray(a[k],np.int16))
  mm=np.zeros(10,np.float32);length=min(10,len(action.get('market',[]))+1);mm[:length]=1;arrays['market_mask'].append(mm)
 assert unknown==0,(r['episode_id'],unknown)
 arrays={k:np.asarray(v,dtype=np.float16 if k in ['global','board','units','unit_mask','market_mask'] else np.int16) for k,v in arrays.items()};arrays['seed']=np.asarray(replay['info']['seed'],np.int64)
 np.savez_compressed(dst,**arrays);return r['episode_id']
def main():
 rows=[r for r in json.loads((SOURCE/'episode_table.json').read_text()) if r['submission_id'] in ['56156662','56216119']]
 manifest=[]
 for r in rows:
  metric=json.loads((SOURCE/'metrics_v2'/f"{r['episode_id']}.json").read_text());seed=metric['seed'];bucket=int(hashlib.sha256(f'majkel-bc-20260915:{seed}'.encode()).hexdigest()[:8],16)%100
  split=('train' if bucket<70 else 'validation' if bucket<85 else 'test') if r['submission_id']=='56156662' else 'version_shift'
  manifest.append({**r,'seed':seed,'split':split})
 # No external-shift episode may share a training seed; remove from external test if any.
 trainseeds={r['seed'] for r in manifest if r['split']=='train'}
 for r in manifest:
  if r['split']=='version_shift' and r['seed'] in trainseeds:r['split']='excluded_shared_seed'
 (B/'split_manifest.json').write_text(json.dumps({'rule':'SHA256(seed), <70 train, 70-84 validation, >=85 test; old version only. New version external shift. Entire episodes grouped. Prior research has inspected this panel, so held-out means optimization held-out, not research-blind.','episodes':manifest},ensure_ascii=False,indent=2))
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:
  for i,_ in enumerate(ex.map(one,rows),1):
   if i%50==0:print('encoded',i,flush=True)
 for split in ['train','validation','test','version_shift']:
  rs=[r for r in manifest if r['split']==split];out=D/split;out.mkdir(exist_ok=True);n=len(rs)*719
  with np.load(D/'episodes'/f"{rs[0]['episode_id']}.npz") as z:maps={k:np.lib.format.open_memmap(out/f'{k}.npy',mode='w+',dtype=z[k].dtype,shape=(n,)+z[k].shape[1:]) for k in z.files if k!='seed'}
  for j,r in enumerate(rs):
   with np.load(D/'episodes'/f"{r['episode_id']}.npz") as z:
    for k,m in maps.items():m[j*719:(j+1)*719]=z[k]
  for m in maps.values():m.flush()
  print('merged',split,len(rs),n,flush=True)
 print('done',flush=True)
if __name__=='__main__':main()
