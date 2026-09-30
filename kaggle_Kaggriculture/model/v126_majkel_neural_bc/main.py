"""V126 independent NumPy neural policy. No replay lookup or parent-agent fallback."""
from pathlib import Path
import copy,time
import numpy as np
import action_space as space
import contract,rules
B=Path(__file__).resolve().parent
class NumpyPolicy:
 def __init__(self,path=None):
  with np.load(path or B/'weights.npz',allow_pickle=False) as z:self.w={k:z[k] for k in z.files}
  self.stats={'calls':0,'unit_mask_changes':0,'market_invalid_stops':0,'quantity_clips':0,'seconds':[]}
 def dense(self,x,name):return x@self.w[name+'/kernel']+self.w[name+'/bias']
 def embed(self,name,idx):return self.w[name+'/embedding'][idx]
 def encode(self,x):
  relu=lambda a:np.maximum(a,0);g=x['global'];board=x['board'];u=x['units'];mask=x['unit_mask'];te=self.embed('time',int(x['step']));bh=relu(self.dense(board,'board'));core=relu(self.dense(np.concatenate([g,bh,te]),'core1'));core=relu(self.dense(core,'core2'))
  uh=relu(self.dense(np.concatenate([u,np.broadcast_to(core,(16,96)),self.embed('role',np.arange(16))],-1),'unit1'));uh=relu(self.dense(uh,'unit2'))
  return core,self.dense(uh,'unit_token'),self.dense(uh,'unit_qty')
 def market(self,core,unit_tokens,unit_mask,tokens,quantities):
  relu=lambda a:np.maximum(a,0);emb=self.embed('unit_context',unit_tokens);pool=(emb*unit_mask[:,None]).sum(0)/max(1,unit_mask.sum());hist=np.concatenate([self.embed('market_history',tokens),np.asarray(quantities,np.float32)[:,None]/100],-1);prefix=(np.cumsum(hist,axis=0)-hist)/10
  inp=np.concatenate([np.broadcast_to(np.concatenate([core,pool]),(10,128)),prefix,self.embed('market_slot',np.arange(10))],-1);mh=relu(self.dense(inp,'market1'));mh=relu(self.dense(mh,'market2'));return self.dense(mh,'market_token'),self.dense(mh,'market_qty')
 def act(self,obs):
  started=time.perf_counter();x=contract.encode(obs);core,ul,uq=self.encode(x);shadow=copy.deepcopy(obs);s=space.seat(obs);n=space.unit_count(obs)
  if n>16:raise ValueError('unit count exceeds trained contract')
  orders=[];ut=np.zeros(16,np.int32)
  # Sequential projection reserves shared seeds/shed and prevents the all-PLANT atomic failure.
  for i in range(n):
   legal=np.asarray(space.unit_legal_mask(shadow,i));raw=int(ul[i].argmax());token=int(np.where(legal,ul[i],-1e9).argmax());self.stats['unit_mask_changes']+=token!=raw
   qm=np.asarray(space.unit_quantity_mask(shadow,i,token));qty=int(np.where(qm,uq[i],-1e9).argmax());order=space.decode_unit(shadow,i,token,qty);ut[i]=token;orders.append(order)
   rules._apply_unit_action(shadow['farms'][s],shadow['private'],i,order,10,int(obs['step'])//24,24,100)
  market=[];mt=np.zeros(10,np.int32);mq=np.zeros(10,np.int32);sh=space.market_shadow(shadow);market_state=copy.deepcopy(obs['market']);market_state['params']=rules._resolve_market_params(market_state.get('params'))
  for slot in range(10):
   ml,ql=self.market(core,ut,x['unit_mask'],mt,mq);token=int(ml[slot].argmax())
   if token==0:break
   if not space.market_legal_mask(sh)[token]:self.stats['market_invalid_stops']+=1;break
   qm=np.asarray(space.market_quantity_mask(sh,token));qty=int(np.where(qm,ql[slot],-1e9).argmax());order=space.apply_market_token(sh,token,qty)
   if order is None:break
   # Correct own marginal market prices; opponent's simultaneous orders remain unknown.
   if order[0] in ['SELL','BUY_PRODUCT']:
    op,item,q=order;farm=shadow['farms'][s];private=shadow['private'];done=0
    for _ in range(q):
     price=rules.market_price(item,market_state['inventory'][item],market_state['params'])
     if not rules._commit_unit(op,item,price,farm,private,market_state,100):break
     done+=1
    if not done:break
    self.stats['quantity_clips']+=done!=q;order[2]=done;sh['money']=farm['money'];sh['shed']=dict(private['shed']);sh['prices']={p:rules.market_price(p,market_state['inventory'][p],market_state['params']) for p in space.PRODUCTS}
   else:
    shadow['farms'][s]['money']=sh['money'];shadow['private']['shed']=dict(sh['shed']);shadow['private']['seeds']=dict(sh['seeds'])
   market.append(order);mt[slot],mq[slot],_=space.market_token(order)
  self.stats['calls']+=1;self.stats['seconds'].append(time.perf_counter()-started)
  return {'farmer':orders[0],'hands':orders[1:],'market':market}
_POLICY=None
def agent(obs,configuration=None):
 global _POLICY
 if _POLICY is None:_POLICY=NumpyPolicy()
 return _POLICY.act(obs)
