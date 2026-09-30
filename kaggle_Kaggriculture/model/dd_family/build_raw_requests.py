"""Extract exact request quantities; preserve joint-action atomic semantics."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
B=Path(__file__).resolve().parent;D=B/'ddap';sys.path.insert(0,str(D));import action_space as space
manifest=json.loads((D/'training_manifest.json').read_text());n=len(manifest['episodes'])
u=np.zeros((719,n,16),np.int32);m=np.zeros((719,n,10),np.int32);ut=np.load(D/'data/unit_tokens.npy',mmap_mode='r');mt=np.load(D/'data/market_tokens.npy',mmap_mode='r');audit=[]
for k,row in enumerate(manifest['episodes']):
 path=Path(row['path']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];d=json.loads(raw);seat=row['seat'];blocked=0;extra=0;large=0
 for t in range(719):
  obs=d['steps'][t][seat]['observation'];act=d['steps'][t+1][seat]['action'];orders=[act.get('farmer',['PASS'])]+act.get('hands',[]);assert len(orders)<=16
  count=space.unit_count(obs)
  if len(orders)>count:extra+=1
  demands={}
  for i,order in enumerate(orders):
   tok,q,known=space.unit_token(order);assert known
   if i<count:assert tok==int(ut[t,k,i])
   else:assert tok==0,('unrepresented non-pass unit',k,t,i,order)
   u[t,k,i]=int(order[2]) if len(order)>2 else 1
   if len(order)>2 and int(order[2])>100:large+=1
   if order[0]=='PLANT':demands[order[1]]=demands.get(order[1],0)+1
  blocked+=any(q>obs['private']['seeds'].get(crop,0) for crop,q in demands.items())
  for i,order in enumerate(act.get('market',[])[:10]):
   tok,q,known=space.market_token(order);assert known and tok==int(mt[t,k,i]);m[t,k,i]=int(order[2]) if len(order)>2 else 1
 audit.append({'prototype':k,'atomic_plant_block_frames':blocked,'extra_hand_frames':extra,'large_unit_requests':large})
np.save(D/'data/raw_unit_quantities.npy',u);np.save(D/'data/raw_market_quantities.npy',m)
(B/'audit_raw_requests.json').write_text(json.dumps({'teacher':'M & M & P & Q','plans':n,'plans_with_atomic_blocks':sum(r['atomic_plant_block_frames']>0 for r in audit),'atomic_block_frames':sum(r['atomic_plant_block_frames'] for r in audit),'rows':audit},indent=2)+'\n');print('plans',n,'atomic block frames',sum(r['atomic_plant_block_frames'] for r in audit),'affected plans',sum(r['atomic_plant_block_frames']>0 for r in audit))
