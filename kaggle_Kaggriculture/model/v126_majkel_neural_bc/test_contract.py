"""Meaningful contract, inference parity, and shared-resource regression checks."""
import json,tempfile,unittest,hashlib
from pathlib import Path
import numpy as np
import jax,jax.numpy as jnp
from flax.traverse_util import flatten_dict
import contract,network,main,action_space as space,rules
B=Path(__file__).resolve().parent

def sample():
 r=next(r for r in json.loads((B/'split_manifest.json').read_text())['episodes'] if r['split']=='train');d=json.loads(Path(r['path']).read_text());o=d['steps'][0][r['seat']]['observation'];o['step']=0;return o
class Tests(unittest.TestCase):
 def test_no_metadata_leakage(self):
  o=sample();a=contract.encode(o);o['remainingOverageTime']=.123;o['EpisodeId']=999;o['seed']=123;o['TeamNames']=['A','B'];b=contract.encode(o)
  for k in a:np.testing.assert_array_equal(a[k],b[k])
 def test_seed_groups_disjoint(self):
  rs=json.loads((B/'split_manifest.json').read_text())['episodes'];groups={s:{r['seed'] for r in rs if r['split']==s} for s in ['train','validation','test']}
  for a in groups:
   for b in groups:
    if a!=b:self.assertFalse(groups[a]&groups[b])
 def test_numpy_parity(self):
  x=contract.encode(sample());b={k:jnp.asarray(v[None]) for k,v in x.items()};b['unit_tokens']=jnp.arange(16)[None]%len(space.UNIT_TOKENS);b['market_tokens']=jnp.arange(10)[None];b['market_quantities']=jnp.arange(10)[None]
  model=network.Policy();p=model.init(jax.random.PRNGKey(0),b)['params'];a=model.apply({'params':p},b)
  with tempfile.TemporaryDirectory() as td:
   file=Path(td)/'weights.npz';np.savez(file,**{'/'.join(k):np.asarray(v) for k,v in flatten_dict(p).items()});policy=main.NumpyPolicy(file);core,ul,uq=policy.encode(x);ml,mq=policy.market(core,np.asarray(b['unit_tokens'][0]),x['unit_mask'],np.arange(10),np.arange(10))
   for key,pred in zip(['unit_tokens','unit_quantities','market_tokens','market_quantities'],[ul,uq,ml,mq]):np.testing.assert_allclose(np.asarray(a[key][0]),pred,atol=2e-5,rtol=2e-5)
 def test_shared_seed_reservation(self):
  o=sample();f=o['farms'][o['player']];f['farmer']=[0,0];f['hands']=[[1,0]];o['private']['inventories']=[{},{}];o['private']['seeds']['WHEAT']=1
  class P(main.NumpyPolicy):
   def encode(self,x):
    ul=np.full((16,len(space.UNIT_TOKENS)),-100.);ul[:,0]=0;ul[:,space.UNIT_INDEX['PLANT:WHEAT']]=10;return np.zeros(96),ul,np.zeros((16,space.QUANTITY_DIM))
   def market(self,*args):return np.eye(10,len(space.MARKET_TOKENS))*0+np.asarray([10]+[0]*(len(space.MARKET_TOKENS)-1)),np.zeros((10,space.QUANTITY_DIM))
  p=P.__new__(P);p.stats={'calls':0,'unit_mask_changes':0,'market_invalid_stops':0,'quantity_clips':0,'seconds':[]};a=p.act(o);self.assertEqual(a['farmer'],['PLANT','WHEAT']);self.assertEqual(a['hands'],[['PASS']]);self.assertEqual(o['private']['seeds']['WHEAT'],1)
if __name__=='__main__':unittest.main()
