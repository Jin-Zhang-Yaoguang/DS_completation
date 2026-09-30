from pathlib import Path
import json,hashlib,concurrent.futures,collections
import numpy as np
import plan_features as F
B=Path(__file__).resolve().parent;D=B/'data';D.mkdir(exist_ok=True);(D/'episodes').mkdir(exist_ok=True)
SOURCE=B.parent/'v126_majkel_neural_bc/split_manifest.json'
def one(r):
 dst=D/'episodes'/f"{r['episode_id']}.npz"
 if dst.exists():return
 raw=Path(r['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256'];d=json.loads(raw);seat=r['seat'];rows=collections.defaultdict(list)
 for day in range(30):
  o=d['steps'][day*24][seat]['observation'];assert o.get('step',day*24)==day*24;o['step']=day*24
  end=d['steps'][min((day+1)*24-1,719)][seat]['observation'];farm=end['farms'][seat]
  for k,v in F.encode(o).items():rows[k].append(v)
  rows['tiles'].append([F.tile_code(t) for row in farm['tiles'] for t in row]);rows['hands'].append(len(farm['hands']));rows['land'].append(len(farm['unlocked_quadrants']))
  rows['current_tiles'].append([F.tile_code(t) for row in o['farms'][seat]['tiles'] for t in row])
  rows['active'].append([float(t!='LOCKED') for row in farm['tiles'] for t in row])
 np.savez_compressed(dst,**{k:np.asarray(v,dtype=np.float32 if k in ['x','active'] else np.int32) for k,v in rows.items()})
def main():
 manifest=json.loads(SOURCE.read_text());(B/'split_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));rs=manifest['episodes']
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as p:
  for i,_ in enumerate(p.map(one,rs),1):
   if i%100==0:print('encoded',i,flush=True)
 for split in ['train','validation','test','version_shift']:
  ss=[r for r in rs if r['split']==split];arrays=collections.defaultdict(list)
  for r in ss:
   with np.load(D/'episodes'/f"{r['episode_id']}.npz") as z:
    for k in z.files:arrays[k].append(z[k])
  np.savez_compressed(D/f'{split}.npz',**{k:np.concatenate(v) for k,v in arrays.items()});print(split,len(ss)*30,flush=True)
if __name__=='__main__':main()
