"""V126 public-state contract; no agent identity, replay ID or future observation."""
import numpy as np
import features
import action_space as space
SHOPS=tuple(features.SHOP_PRODUCTS)
MAX_UNITS=16

def encode(obs):
 x=features.encode_observation(obs)
 shops=np.zeros((8,9),np.float32)
 names=obs.get('town',{}).get('unlocked_shops',[])
 for i in range(8):shops[i,SHOPS.index(names[i])+1 if i<len(names) else 0]=1
 x['global']=np.concatenate([x['global'],shops.ravel(),[space.seat(obs)],x['board'].mean(axis=(1,2)).ravel()]).astype(np.float32)
 x['board']=x['board'][0].reshape(-1)
 x['step']=np.asarray(int(obs['step']),np.int32)
 return x
