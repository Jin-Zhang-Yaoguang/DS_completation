"""Daily public observation -> economic and spatial features; no future IDs."""
import numpy as np
import features
SHOPS=tuple(features.SHOP_PRODUCTS)
CROPS=('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON')
ANIMALS=('GOOSE','COW','SHEEP')
TYPES=('EMPTY',)+CROPS+ANIMALS

def encode(obs):
 x=features.encode_observation(obs);shop=np.zeros((8,9),np.float32)
 names=obs.get('town',{}).get('unlocked_shops',[])
 for i in range(8):shop[i,SHOPS.index(names[i])+1 if i<len(names) else 0]=1
 g=np.concatenate([x['global'],shop.ravel(),[obs['player']],x['board'].mean(axis=(1,2)).ravel(),x['board'][0].ravel()]).astype(np.float32)
 return {'x':g,'day':np.asarray(obs['step']//24,np.int32)}
def tile_code(t):
 name=(t.get('animal') or t.get('crop')) if isinstance(t,dict) else None
 return TYPES.index(name) if name in TYPES else 0
